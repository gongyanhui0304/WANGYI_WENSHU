#!/usr/bin/env node
// Package generated per-user SKILL.md files into one clean delivery folder.
// Usage:
//   node client/package_skill_only_delivery.mjs --users Benson chenzeyi Sherman WangLei

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, "..");

function fail(message) {
  console.error(message);
  process.exit(1);
}

function readUsers(argv) {
  const idx = argv.indexOf("--users");
  if (idx === -1) return [];
  const users = [];
  for (let i = idx + 1; i < argv.length; i += 1) {
    if (argv[i].startsWith("--")) break;
    users.push(argv[i]);
  }
  return users;
}

const users = readUsers(process.argv);
if (!users.length) fail("missing --users <user-id>...");

function localStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return [
    d.getFullYear(),
    pad(d.getMonth() + 1),
    pad(d.getDate()),
    "-",
    pad(d.getHours()),
    pad(d.getMinutes()),
    pad(d.getSeconds()),
  ].join("");
}

const stamp = localStamp();
const releaseDir = path.join(projectRoot, "dist", "release", `skill-md-only-${stamp}`);
fs.mkdirSync(releaseDir, { recursive: true });

const copied = [];
for (const user of users) {
  const source = path.join(projectRoot, "dist", "platform-delivery", user, "user", "SKILL.md");
  if (!fs.existsSync(source)) fail(`missing generated SKILL.md for ${user}: ${source}`);
  const target = path.join(releaseDir, `${user}_SKILL.md`);
  fs.copyFileSync(source, target);
  copied.push(path.basename(target));
}

const zipPath = `${releaseDir}.zip`;
const ps = [
  "$ErrorActionPreference='Stop'",
  `Compress-Archive -Path '${releaseDir.replace(/'/g, "''")}\\*_SKILL.md' -DestinationPath '${zipPath.replace(/'/g, "''")}' -CompressionLevel Optimal`,
].join("; ");
const child = spawnSync("powershell", ["-NoProfile", "-Command", ps], { encoding: "utf8" });
if (child.status !== 0) {
  process.stderr.write(String(child.stderr || child.stdout || "Compress-Archive failed"));
  process.exit(child.status || 1);
}

console.log(JSON.stringify({
  release_dir: releaseDir,
  release_zip: zipPath,
  files: copied,
}, null, 2));
