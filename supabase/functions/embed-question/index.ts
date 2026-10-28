import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { corsHeaders, json } from "../_shared/cors.ts";
import { requireUser } from "../_shared/auth.ts";

const MAX_QUESTION_CHARS = 500;

// POST { question } -> { embedding: number[1536] }
Deno.serve(async (req) => {
    if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders(req) });

    const user = await requireUser(req);
    if (user instanceof Response) return user;

    try {
        const { question } = await req.json();
        if (typeof question !== "string" || !question.trim()) {
            return json(req, { error: "Missing or invalid 'question'" }, 400);
        }
        if (question.length > MAX_QUESTION_CHARS) {
            return json(req, { error: `Question must be under ${MAX_QUESTION_CHARS} characters` }, 400);
        }

        // The OpenAI key lives only here, as a Supabase secret; the browser never sees it.
        const response = await fetch("https://api.openai.com/v1/embeddings", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${Deno.env.get("OPENAI_API_KEY")}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ model: "text-embedding-3-small", input: question }),
        });
        if (!response.ok) return json(req, { error: "Embedding request failed" }, 502);

        const data = await response.json();
        return json(req, { embedding: data.data[0].embedding });
    } catch (err) {
        return json(req, { error: (err as Error).message }, 500);
    }
});
