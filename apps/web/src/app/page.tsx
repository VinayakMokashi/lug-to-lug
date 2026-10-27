import Link from "next/link";

import { CaseEllipse } from "@/components/case-ellipse";
import { PLAN_URL, REPO_URL } from "@/lib/links";

const linkClass =
  "rounded-full border border-line px-4 py-2 transition-colors hover:border-accent hover:text-accent";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-10 px-6 py-16">
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">
        Lug to Lug · in development
      </p>
      <h1 className="text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
        Try any watch on your own wrist at true size, with the error bar to
        prove it.
      </h1>
      <CaseEllipse />
      <p className="max-w-2xl text-lg leading-relaxed text-muted">
        The watch you already wear is the ruler. Its round case appears as an
        ellipse in a photo: the long axis is the known diameter, which gives the
        scale, and the ratio of the axes gives the tilt of your wrist. Lug to
        Lug measures from it, then shows any other watch on your wrist at its
        real size, with its sizing error printed on the render.
      </p>
      <nav className="flex flex-wrap gap-3 text-sm" aria-label="Project links">
        <a className={linkClass} href={REPO_URL}>
          Source on GitHub
        </a>
        <a className={linkClass} href={PLAN_URL}>
          Build plan
        </a>
        <Link className={linkClass} href="/status">
          System status
        </Link>
      </nav>
      <p className="font-mono text-xs text-muted">
        The try-on isn&apos;t live yet. This page is the deployment skeleton.
      </p>
    </main>
  );
}
