import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from datetime import timedelta
from pathlib import Path
from unittest import mock

from touchgrass import cli, server, state, tunnel, verify


class TempHome(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.dict(os.environ, {"TOUCHGRASS_HOME": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)


class FreshnessTest(unittest.TestCase):
    def test_missing_time_rejected(self):
        self.assertIn("camera", verify.check_freshness(None, 0))

    def test_old_photo_rejected(self):
        self.assertIn("minutes old", verify.check_freshness(0, 20 * 60 * 1000))

    def test_future_photo_rejected(self):
        self.assertIn("future", verify.check_freshness(5 * 60 * 1000, 0))

    def test_fresh_photo_ok(self):
        self.assertIsNone(verify.check_freshness(1000, 60 * 1000))


class JudgeTest(unittest.TestCase):
    def test_pass(self):
        v = verify.judge({"outdoors": True, "sky_or_plants": True, "photo_of_screen": False, "roast": "hi"})
        self.assertTrue(v.passed)
        self.assertEqual(v.roast, "hi")

    def test_screen_photo_fails_even_if_outdoors(self):
        v = verify.judge({"outdoors": True, "sky_or_plants": True, "photo_of_screen": True})
        self.assertFalse(v.passed)
        self.assertIn("screen", v.reason)

    def test_indoors_fails(self):
        self.assertFalse(verify.judge({"outdoors": False, "sky_or_plants": True}).passed)

    def test_string_booleans(self):
        v = verify.judge({"outdoors": "true", "sky_or_plants": "yes", "photo_of_screen": "false"})
        self.assertTrue(v.passed)

    def test_parse_output_with_surrounding_text(self):
        self.assertEqual(verify.parse_model_output('sure! {"outdoors": true} done'), {"outdoors": True})

    def test_parse_output_without_json(self):
        with self.assertRaises(verify.ModelError):
            verify.parse_model_output("I can't see images")


class PipelineTest(unittest.TestCase):
    PASS = {"outdoors": True, "sky_or_plants": True, "photo_of_screen": False, "roast": "r"}

    def test_screen_double_check_vetoes_a_pass(self):
        answers = [self.PASS, {"on_screen": True}]
        with mock.patch.object(verify, "ask_model", side_effect=lambda *a, **k: answers.pop(0)):
            v = verify.check(b"x")
        self.assertFalse(v.passed)
        self.assertEqual(v.reason, verify.SCREEN_REASON)

    def test_double_check_clears_real_photo(self):
        answers = [self.PASS, {"on_screen": False}]
        with mock.patch.object(verify, "ask_model", side_effect=lambda *a, **k: answers.pop(0)):
            self.assertTrue(verify.check(b"x").passed)

    def test_failures_skip_double_check(self):
        with mock.patch.object(verify, "ask_model", return_value={"outdoors": False}) as ask:
            self.assertFalse(verify.check(b"x").passed)
        self.assertEqual(ask.call_count, 1)

    def test_stale_photo_never_reaches_model(self):
        with mock.patch.object(verify, "ask_model") as ask:
            self.assertFalse(verify.verify(b"x", 0, 60 * 60 * 1000).passed)
        ask.assert_not_called()


class AskModelTest(unittest.TestCase):
    def _http_error(self, code, body):
        return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(body))

    def _ok(self, text):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"response": text}).encode()
        return response

    def test_retries_without_format_when_structured_output_unavailable(self):
        bodies = []
        replies = [self._http_error(501, b'{"error":"structured output is unavailable"}'),
                   self._ok('```json\n{"outdoors": true}\n```')]

        def fake_urlopen(request, timeout):
            bodies.append(json.loads(request.data))
            reply = replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

        with mock.patch.object(urllib.request, "urlopen", side_effect=fake_urlopen):
            self.assertEqual(verify.ask_model(b"x"), {"outdoors": True})
        self.assertEqual(bodies[0]["format"], "json")
        self.assertNotIn("format", bodies[1])
        self.assertFalse(bodies[1]["think"])

    def test_other_http_errors_are_reported_not_called_unreachable(self):
        error = self._http_error(404, b'{"error":"model not found"}')
        with mock.patch.object(urllib.request, "urlopen", side_effect=error):
            with self.assertRaisesRegex(verify.ModelError, "404.*model not found"):
                verify.ask_model(b"x")


class CheckTest(TempHome):
    def test_first_run_does_not_block(self):
        self.assertEqual(cli.main(["check"]), 0)

    def test_blocks_after_limit(self):
        state.mark_grass(state.now() - timedelta(minutes=state.max_minutes() + 1))
        self.assertEqual(cli.main(["check"]), 1)

    def test_allows_within_limit(self):
        state.mark_grass(state.now() - timedelta(minutes=10))
        self.assertEqual(cli.main(["check"]), 0)


class InstallTest(TempHome):
    def test_installs_hook_and_respects_existing(self):
        repo = Path(self.tmp.name) / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        cwd = os.getcwd()
        os.chdir(repo)
        try:
            self.assertEqual(cli.main(["install"]), 0)
            hook = repo / ".git" / "hooks" / "pre-push"
            self.assertIn(cli.HOOK_MARKER, hook.read_text())
            self.assertTrue(os.access(hook, os.X_OK))

            hook.write_text("#!/bin/sh\necho mine\n")
            self.assertEqual(cli.main(["install"]), 1)
            self.assertEqual(cli.main(["install", "--force"]), 0)
            self.assertIn(cli.HOOK_MARKER, hook.read_text())
        finally:
            os.chdir(cwd)

    def test_hook_blocks_real_push(self):
        root = Path(self.tmp.name)
        remote, repo = root / "remote.git", root / "repo"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "x"], check=True)
        subprocess.run(git + ["remote", "add", "origin", str(remote)], check=True)
        cwd = os.getcwd()
        os.chdir(repo)
        try:
            cli.main(["install"])
        finally:
            os.chdir(cwd)
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}

        state.mark_grass(state.now() - timedelta(hours=5))
        blocked = subprocess.run(git + ["push", "-q", "origin", "HEAD"], capture_output=True, text=True, env=env)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("Push blocked", blocked.stderr)

        state.mark_grass()
        allowed = subprocess.run(git + ["push", "-q", "origin", "HEAD"], capture_output=True, text=True, env=env)
        self.assertEqual(allowed.returncode, 0, allowed.stderr)


class ServerTest(TempHome):
    def _run(self, verdict, **serve_kwargs):
        ready = threading.Event()
        urls = []
        result = []

        def on_ready(url):
            urls.append(url.replace(server.lan_ip(), "127.0.0.1"))
            ready.set()

        def fake_verifier(jpeg, taken_at, now_ms):
            self.assertEqual(jpeg, b"jpegbytes")
            return verdict

        t = threading.Thread(
            target=lambda: result.append(
                server.serve(on_ready, port=0, verifier=fake_verifier, timeout_minutes=0.02, **serve_kwargs)
            )
        )
        t.start()
        self.assertTrue(ready.wait(5))
        url = urls[0]
        token_query = url[url.index("?"):]

        with urllib.request.urlopen(url) as r:
            self.assertIn(b"touch grass", r.read())
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(url.replace(token_query, "?t=wrong"))

        body = json.dumps({"image": "data:image/jpeg;base64,anBlZ2J5dGVz", "taken_at": 1}).encode()
        req = urllib.request.Request(
            url.replace("/?", "/upload?"), data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            self.assertEqual(r.status, 202)
            job = json.loads(r.read())["job"]
        result_url = url.replace("/?", "/result?") + "&job=" + job
        for _ in range(50):
            with urllib.request.urlopen(result_url) as r:
                response = json.loads(r.read())
            if not response.get("pending"):
                break
            time.sleep(0.05)
        t.join(5)
        return response, result[0]

    def test_pass_unlocks_and_records_receipt(self):
        state.mark_grass(state.now() - timedelta(hours=4))
        response, verdict = self._run(verify.Verdict(True, "Grass confirmed.", "A park.", "Wow, sunlight."))
        self.assertTrue(response["passed"])
        self.assertIsNotNone(verdict)
        self.assertLess(state.minutes_indoors(), 1)
        receipt = state.receipts()[-1]
        self.assertEqual(receipt["roast"], "Wow, sunlight.")
        self.assertGreaterEqual(receipt["indoors_minutes"], 239)

    def test_pass_recorded_even_if_phone_never_asks_for_result(self):
        passed = []
        handler = server.make_handler("tok", lambda *a: verify.Verdict(True, "ok"), passed.append)
        h = handler.__new__(handler)
        body = json.dumps({"image": "data:image/jpeg;base64,eA==", "taken_at": 1}).encode()
        h.path = "/upload?t=tok"
        h.headers = {"Content-Length": str(len(body))}
        h.rfile = io.BytesIO(body)
        with mock.patch.object(handler, "_json"):
            h.do_POST()
        for _ in range(50):
            if passed:
                break
            time.sleep(0.02)
        self.assertEqual(len(passed), 1)

    def test_model_error_reaches_the_phone(self):
        def broken(*a):
            raise verify.ModelError("Ollama returned 500: boom")

        sent = []
        handler = server.make_handler("tok", broken, lambda v: None)

        def request(method, path, body=b""):
            h = handler.__new__(handler)
            h.path = path
            h.headers = {"Content-Length": str(len(body))}
            h.rfile = io.BytesIO(body)
            with mock.patch.object(handler, "_json", side_effect=lambda status, payload: sent.append(payload)):
                getattr(h, method)()
            return sent[-1]

        body = json.dumps({"image": "data:image/jpeg;base64,eA=="}).encode()
        job = request("do_POST", "/upload?t=tok", body)["job"]
        for _ in range(50):
            result = request("do_GET", f"/result?t=tok&job={job}")
            if not result.get("pending"):
                break
            time.sleep(0.02)
        self.assertIn("boom", result["error"])

    def test_fail_keeps_blocked(self):
        state.mark_grass(state.now() - timedelta(hours=4))
        seen = []
        response, verdict = self._run(verify.Verdict(False, "That's a picture of a screen."), on_verdict=seen.append)
        self.assertFalse(response["passed"])
        self.assertEqual([v.reason for v in seen], ["That's a picture of a screen."])
        self.assertIsNone(verdict)
        self.assertGreater(state.minutes_indoors(), 200)
        self.assertEqual(state.receipts(), [])


class KeepPhotosTest(TempHome):
    def test_photos_not_kept_by_default(self):
        server.keep_photo(b"jpeg")
        self.assertFalse((state.home() / "photos").exists())

    def test_photos_kept_when_asked(self):
        with mock.patch.dict(os.environ, {"TOUCHGRASS_KEEP_PHOTOS": "1"}):
            server.keep_photo(b"jpeg")
        self.assertEqual([p.read_bytes() for p in (state.home() / "photos").iterdir()], [b"jpeg"])

class PublicUrlTest(TempHome):
    def test_public_url_listens_on_localhost_only_with_long_token(self):
        bound = []
        real = server.ThreadingHTTPServer

        def spy(address, handler):
            bound.append(address)
            return real(("127.0.0.1", 0), handler)

        urls = []
        with mock.patch.object(server, "ThreadingHTTPServer", side_effect=spy):
            server.serve(urls.append, port=0, timeout_minutes=0, public_url="https://grass.example.com/")
        self.assertEqual(bound[0][0], "127.0.0.1")
        self.assertTrue(urls[0].startswith("https://grass.example.com/?t="))
        self.assertGreaterEqual(len(urls[0].split("?t=")[1]), 20)


class TunnelTest(unittest.TestCase):
    def test_finds_quick_tunnel_url_in_cloudflared_log(self):
        line = "2026-10-10T12:00:00Z INF |  https://calm-grass-tree.trycloudflare.com  |"
        self.assertEqual(tunnel.find_url(line), "https://calm-grass-tree.trycloudflare.com")
        self.assertIsNone(tunnel.find_url("INF Requesting new quick Tunnel on trycloudflare.com..."))

    def test_missing_cloudflared_says_how_to_install(self):
        with self.assertRaisesRegex(tunnel.TunnelError, "brew install cloudflared"):
            tunnel.Tunnel(8765, binary="definitely-not-cloudflared").open()

    def _fake_cloudflared(self, script):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "cloudflared"
        path.write_text("#!/bin/sh\n" + script)
        path.chmod(0o755)
        return str(path)

    def test_reads_url_from_a_running_process_and_stops_it(self):
        fake = self._fake_cloudflared(
            'echo "INF starting" >&2\necho "INF |  https://abc-def.trycloudflare.com  |" >&2\nsleep 30\n'
        )
        t = tunnel.Tunnel(8765, binary=fake)
        self.assertEqual(t.open(timeout=5), "https://abc-def.trycloudflare.com")
        t.close()
        self.assertIsNotNone(t.process.poll())

    def test_process_that_exits_without_url_is_an_error(self):
        fake = self._fake_cloudflared('echo "ERR failed to request quick Tunnel" >&2\nexit 1\n')
        with self.assertRaisesRegex(tunnel.TunnelError, "failed to request quick Tunnel"):
            tunnel.Tunnel(8765, binary=fake).open(timeout=5)

    def test_cli_reports_tunnel_errors_instead_of_crashing(self):
        with mock.patch.object(cli, "serve", side_effect=tunnel.TunnelError("nope")):
            with mock.patch("sys.stderr", new=io.StringIO()) as err:
                self.assertEqual(cli.main(["prove", "--tunnel"]), 1)
        self.assertIn("nope", err.getvalue())


if __name__ == "__main__":
    unittest.main()
