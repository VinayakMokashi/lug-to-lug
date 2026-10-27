import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { buildInfo } from "@/lib/build-info";

export const metadata: Metadata = { title: "Status · Lug to Lug" };

type ApiHealth = {
  status: string;
  service: string;
  version: string;
  core_version: string;
  environment: string;
  git_sha: string;
};

type Probe =
  | { ok: true; health: ApiHealth; millis: number }
  | { ok: false; error: string };

async function probeApi(): Promise<Probe> {
  const base = process.env.API_URL;
  if (!base) return { ok: false, error: "API_URL is not set" };
  const started = performance.now();
  try {
    const response = await fetch(new URL("/health", base), {
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
    if (!response.ok) return { ok: false, error: `HTTP ${response.status}` };
    const health = (await response.json()) as ApiHealth;
    return {
      ok: true,
      health,
      millis: Math.round(performance.now() - started),
    };
  } catch (error) {
    return {
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-6 border-b border-line py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="font-mono">{value}</dd>
    </div>
  );
}

async function Services() {
  await connection();
  const web = buildInfo();
  const api = await probeApi();
  return (
    <div className="grid gap-10">
      <section>
        <h2 className="mb-2 text-lg font-medium">Web</h2>
        <dl>
          <Row label="Status" value="ok" />
          <Row label="Environment" value={web.environment} />
          <Row label="Commit" value={web.gitSha} />
        </dl>
      </section>
      <section>
        <h2 className="mb-2 text-lg font-medium">API</h2>
        {api.ok ? (
          <dl>
            <Row label="Status" value={api.health.status} />
            <Row label="Version" value={api.health.version} />
            <Row label="Core version" value={api.health.core_version} />
            <Row label="Environment" value={api.health.environment} />
            <Row label="Commit" value={api.health.git_sha} />
            <Row label="Round trip" value={`${api.millis} ms`} />
          </dl>
        ) : (
          <p className="font-mono text-sm text-accent">
            Unreachable: {api.error}
          </p>
        )}
      </section>
    </div>
  );
}

export default function StatusPage() {
  return (
    <main className="mx-auto flex w-full max-w-xl flex-1 flex-col gap-8 px-6 py-16">
      <Link
        href="/"
        className="font-mono text-xs uppercase tracking-[0.2em] text-muted hover:text-accent"
      >
        ← Lug to Lug
      </Link>
      <h1 className="text-3xl font-semibold tracking-tight">System status</h1>
      <Suspense fallback={<p className="text-muted">Checking the services…</p>}>
        <Services />
      </Suspense>
    </main>
  );
}
