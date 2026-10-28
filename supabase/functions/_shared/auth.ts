import { createClient } from "jsr:@supabase/supabase-js@2";
import { json } from "./cors.ts";

/**
 * Verify the caller is a logged-in user before we spend OpenAI money.
 *
 * Functions are deployed with --no-verify-jwt because the gateway can't yet
 * verify Supabase Auth's newer asymmetric (ES256) session tokens. So we check
 * the token here: auth.getUser() asks Supabase Auth whether this JWT is a real,
 * unexpired session. The public anon key alone is NOT a user session, so it fails.
 *
 * SUPABASE_URL and SUPABASE_ANON_KEY are injected into every Edge Function.
 */
export async function requireUser(req: Request): Promise<{ id: string } | Response> {
    const authHeader = req.headers.get("Authorization");
    if (!authHeader) return json(req, { error: "Missing Authorization header" }, 401);

    const supabase = createClient(
        Deno.env.get("SUPABASE_URL")!,
        Deno.env.get("SUPABASE_ANON_KEY")!,
        { global: { headers: { Authorization: authHeader } } },
    );
    const { data: { user }, error } = await supabase.auth.getUser();
    if (error || !user) return json(req, { error: "Invalid or expired session" }, 401);

    return { id: user.id };
}
