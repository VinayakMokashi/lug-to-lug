import { connection } from "next/server";

import { buildInfo } from "@/lib/build-info";

/** Liveness check for Cloud Run and the smoke test. */
export async function GET() {
  await connection();
  const { environment, gitSha } = buildInfo();
  return Response.json({
    status: "ok",
    service: "web",
    environment,
    git_sha: gitSha,
  });
}
