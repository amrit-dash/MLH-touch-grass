import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from datetime import timedelta
from pathlib import Path
from unittest import mock

from touchgrass import cli, server, state, verify


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
    def _run(self, verdict):
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
                server.serve(on_ready, port=0, verifier=fake_verifier, timeout_minutes=0.02)
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
            response = json.loads(r.read())
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

    def test_pass_recorded_even_if_phone_disconnects(self):
        state.mark_grass(state.now() - timedelta(hours=4))
        passed = []
        handler = server.make_handler("tok", lambda *a: verify.Verdict(True, "ok"), passed.append)
        h = handler.__new__(handler)
        body = json.dumps({"image": "data:image/jpeg;base64,eA==", "taken_at": 1}).encode()
        h.path = "/upload?t=tok"
        h.headers = {"Content-Length": str(len(body))}
        h.rfile = io.BytesIO(body)
        with mock.patch.object(handler, "_json", side_effect=BrokenPipeError):
            with self.assertRaises(BrokenPipeError):
                h.do_POST()
        self.assertEqual(len(passed), 1)

    def test_fail_keeps_blocked(self):
        state.mark_grass(state.now() - timedelta(hours=4))
        response, verdict = self._run(verify.Verdict(False, "That's a picture of a screen."))
        self.assertFalse(response["passed"])
        self.assertIsNone(verdict)
        self.assertGreater(state.minutes_indoors(), 200)
        self.assertEqual(state.receipts(), [])


if __name__ == "__main__":
    unittest.main()
