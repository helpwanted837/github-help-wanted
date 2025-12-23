export async function onRequest(context: any) {
  const request = context.request as Request;
  const url = new URL(request.url);

  if (url.pathname !== "/") {
    return context.next();
  }

  const languages = (url.searchParams.get("languages") || "").toLowerCase();
  const labels = (url.searchParams.get("labels") || "").toLowerCase();

  const redirect = (toPath: string) => {
    const target = new URL(toPath, url.origin);
    return Response.redirect(target.toString(), 301);
  };

  if (languages.includes("python")) return redirect("/open-source/python/");
  if (languages.includes("javascript")) return redirect("/open-source/javascript/");

  if (labels.includes("hacktoberfest")) return redirect("/open-source/hacktoberfest/");
  if (labels.includes("help wanted") || labels.includes("good first issue")) {
    return redirect("/open-source/good-first-issue/");
  }

  if (url.search) return redirect("/");
  return context.next();
}

