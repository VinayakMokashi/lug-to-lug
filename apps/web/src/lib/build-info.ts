/** Deploy details, set as environment variables by the deploy. Read them at request time. */
export function buildInfo() {
  return {
    environment: process.env.ENVIRONMENT ?? "local",
    gitSha: process.env.GIT_SHA ?? "unknown",
  };
}
