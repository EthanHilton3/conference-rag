// Browsers only let these origins read our responses. CORS is enforced by the
// browser, not the server: curl ignores it, so auth (auth.ts) is the real gate.
const ALLOWED_ORIGINS = [
    "https://ethanhilton3.github.io",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
];

export function corsHeaders(req: Request): Record<string, string> {
    const origin = req.headers.get("Origin") ?? "";
    return {
        "Access-Control-Allow-Origin": ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
        "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
        "Vary": "Origin",
    };
}

export function json(req: Request, body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { ...corsHeaders(req), "Content-Type": "application/json" },
    });
}
