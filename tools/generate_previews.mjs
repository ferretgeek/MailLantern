import { access, stat } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require("sharp");
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = process.argv[2];

if (!source) throw new Error("Pass the path to a real 1280×720 browser screenshot.");
await access(source);

const dashboard = resolve(root, "docs/images/dashboard.png");
const social = resolve(root, "docs/images/social-preview.png");
const metadata = await sharp(source).metadata();
if (!metadata.width || !metadata.height || metadata.width < 1000) {
  throw new Error("Expected a desktop browser screenshot.");
}
// Browser QA captures include the 13 px vertical scrollbar; exclude browser chrome.
const image = sharp(source)
  .extract({ left: 0, top: 0, width: metadata.width - 13, height: metadata.height })
  .flatten({ background: "#edf7ff" });

await image
  .clone()
  .resize(1280, 720, { fit: "cover", position: "top" })
  .png({ compressionLevel: 9, palette: true, quality: 92 })
  .toFile(dashboard);

await image
  .clone()
  .resize(1280, 640, { fit: "cover", position: "top" })
  .png({ compressionLevel: 9, palette: true, quality: 92 })
  .toFile(social);

if ((await stat(social)).size >= 1_000_000) throw new Error("Social preview must remain below 1 MB.");
