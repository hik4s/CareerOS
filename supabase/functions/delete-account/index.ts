import { createClient } from "npm:@supabase/supabase-js@2.110.0";

const url = Deno.env.get("SUPABASE_URL")!;
const admin = createClient(url, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false, autoRefreshToken: false },
});
const response = (status: number, detail: string) =>
  Response.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });

Deno.serve(async (request) => {
  if (request.method !== "POST") return response(405, "Método inválido.");
  const token = request.headers.get("Authorization")?.match(/^Bearer ([^\s]+)$/i)?.[1];
  if (!token) return response(401, "Entre novamente.");
  const { data, error } = await admin.auth.getUser(token);
  if (error || !data.user || data.user.is_anonymous) return response(401, "Entre novamente.");
  const payload = await request.json().catch(() => null);
  if (payload?.confirmation !== "EXCLUIR") return response(400, "Confirmação necessária.");

  // The folder and user ID come exclusively from the verified session.
  const owner = data.user.id;
  const bucket = admin.storage.from("career-resumes");
  const folders = [owner];
  const files: string[] = [];
  while (folders.length) {
    const folder = folders.pop()!;
    for (let offset = 0;; offset += 100) {
      const { data: entries, error: listError } = await bucket.list(folder, {
        limit: 100, offset, sortBy: { column: "name", order: "asc" },
      });
      if (listError) return response(502, "Não foi possível listar seus arquivos.");
      for (const entry of entries) {
        if (!entry.name || entry.name.includes("/") || [".", ".."].includes(entry.name)) {
          return response(502, "Não foi possível verificar seus arquivos.");
        }
        const path = folder + "/" + entry.name;
        if (entry.id) files.push(path);
        else folders.push(path);
      }
      if (entries.length < 100) break;
    }
  }
  for (let index = 0; index < files.length; index += 100) {
    const { error: removeError } = await bucket.remove(files.slice(index, index + 100));
    if (removeError) return response(502, "Não foi possível remover todos os arquivos. Tente novamente.");
  }
  const { error: deleteError } = await admin.auth.admin.deleteUser(owner);
  if (deleteError) return response(502, "Não foi possível concluir a exclusão. Tente novamente.");
  return new Response(null, { status: 204, headers: { "Cache-Control": "no-store" } });
});
