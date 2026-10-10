// Drive the real phone page against a real `touchgrass prove` and a real model.
// node scripts/e2e_phone.mjs REPO_DIR OUT_DIR CHEAT_PHOTO PASS_PHOTO  (needs Playwright + Ollama)
import { chromium, devices } from "playwright";
import { spawn } from "node:child_process";
import { utimesSync } from "node:fs";

const [repo, outDir, failPhoto, passPhoto] = process.argv.slice(2);
const proc = spawn("python3", ["-m", "touchgrass", "prove", "--port", "8799"], { cwd: repo, env: process.env });
let out = "";
const exited = new Promise(res => proc.on("exit", res));
proc.stdout.on("data", d => { out += d; process.stdout.write(d); });
proc.stderr.on("data", d => process.stderr.write(d));
const url = await new Promise(res => {
  const t = setInterval(() => { const m = out.match(/http:\/\/\S+\?t=\S+/); if (m) { clearInterval(t); res(m[0]); } }, 200);
});
const local = url.replace(/\/\/[^:]+:/, "//127.0.0.1:");

const browser = await chromium.launch();
const page = await (await browser.newContext({ ...devices["iPhone 13"], colorScheme: "light" })).newPage();
await page.goto(local);
await page.screenshot({ path: `${outDir}/phone-1-start.png` });

for (const [photo, name] of [[failPhoto, "phone-2-cheat"], [passPhoto, "phone-3-pass"]]) {
  const now = new Date(); utimesSync(photo, now, now);  // a fresh capture
  const done = page.waitForResponse(
    async r => r.url().includes("/result") && !(await r.json()).pending, { timeout: 900000 });
  await page.setInputFiles("#photo", photo);
  console.log(name, JSON.stringify(await (await done).json()));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${outDir}/${name}.png`, fullPage: true });
}
await browser.close();
const code = await Promise.race([exited, new Promise(res => setTimeout(() => { proc.kill(); res("killed"); }, 5000))]);
console.log("prove exited", code);
