// Generate the TypeScript data contracts from the JSON Schemas in data/schemas.
//
//   pnpm contracts         write src/lib/contracts/*.ts
//   pnpm contracts:check   fail if they are out of date (part of `pnpm check`)
//
// The schemas are the single source of truth (ADR-0004); the Python side generates its
// Pydantic models from the same files (scripts/contracts.py at the repository root).
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { compileFromFile } from "json-schema-to-typescript";
import { format, resolveConfig } from "prettier";

const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const schemas = path.resolve(web, "..", "..", "data", "schemas");
const target = path.join(web, "src", "lib", "contracts");

// The contracts the web app uses: schema file -> generated module.
const modules = {
  "stand-in-spec.schema.json": "stand-in-spec.ts",
  "catalogue-entry.schema.json": "catalogue-entry.ts",
};

async function generate(schema) {
  const banner = [
    `// Generated from data/schemas/${schema} by scripts/contracts.mjs.`,
    "// Do not edit: change the schema, then run `pnpm contracts`.",
  ].join("\n");
  const code = await compileFromFile(path.join(schemas, schema), {
    cwd: schemas,
    bannerComment: banner,
    additionalProperties: false,
    format: false,
  });
  const file = path.join(target, modules[schema]);
  const options = (await resolveConfig(file)) ?? {};
  return format(code, { ...options, filepath: file });
}

async function current(file) {
  try {
    return await readFile(file, "utf8");
  } catch {
    return null;
  }
}

const check = process.argv.includes("--check");
const stale = [];
for (const [schema, module] of Object.entries(modules)) {
  const file = path.join(target, module);
  const fresh = await generate(schema);
  if (fresh === (await current(file))) continue;
  if (check) {
    stale.push(path.relative(web, file));
  } else {
    await writeFile(file, fresh, "utf8");
    console.log(`wrote ${path.relative(web, file)}`);
  }
}

if (stale.length > 0) {
  console.error("Out of date with data/schemas (run `pnpm contracts`):");
  for (const file of stale) console.error(`  ${file}`);
  process.exit(1);
}
if (check) console.log("Contracts are up to date.");
