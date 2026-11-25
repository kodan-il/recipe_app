import { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function App() {
  const [inputText, setInputText] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  // Menyimpan detail resep yang sudah dibuka per URL: { [url]: recipeObject }
  const [detailsByUrl, setDetailsByUrl] = useState({});
  const [loadingUrl, setLoadingUrl] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSearch = async (e) => {
    e.preventDefault();
    setErrorMsg("");

    const ingredients = inputText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    if (ingredients.length === 0) {
      setErrorMsg("Please enter at least one ingredient (EN or ID).");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/recipes/by-ingredients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ingredients),
      });
      const data = await res.json();
      setResults(Array.isArray(data.results) ? data.results : []);
    } catch (err) {
      setErrorMsg("Failed to fetch recipes from backend.");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDetail = async (url) => {
    if (!url) return;
    if (detailsByUrl[url]) return; // Sudah ter-load sebelumnya

    setLoadingUrl(url);
    try {
      const res = await fetch(
        `${API_BASE}/api/recipes/detail?url=${encodeURIComponent(url)}`
      );
      const data = await res.json();
      if (data.recipe) {
        setDetailsByUrl((prev) => ({ ...prev, [url]: data.recipe }));
      }
    } catch (err) {
      console.error("Failed to load detail:", err);
    } finally {
      setLoadingUrl(null);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>Recipe Finder</h1>

      <form onSubmit={handleSearch} style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Type ingredients (e.g. egg, tofu or telur, tahu)"
          style={{ flex: 1, padding: 10 }}
        />
        <button type="submit" disabled={loading} style={{ padding: "10px 18px" }}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {errorMsg && <p style={{ color: "crimson" }}>{errorMsg}</p>}

      <div style={{ display: "grid", gap: 16 }}>
        {results.map((item, idx) => {
          const r = item.recipe || {};
          const url = r.url || "";
          const detail = detailsByUrl[url];
          const matched = Array.isArray(item.matched_ingredients)
            ? item.matched_ingredients
            : [];

          return (
            <div
              key={url || idx}
              style={{
                border: "1px solid #444",
                borderRadius: 10,
                padding: 16,
              }}
            >
              <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                {r.image && (
                  <img
                    src={r.image}
                    alt={r.title}
                    style={{ width: 96, height: 96, objectFit: "cover", borderRadius: 8 }}
                  />
                )}
                <div style={{ flex: 1 }}>
                  <h2 style={{ margin: "0 0 6px" }}>{r.title}</h2>
                  <p style={{ margin: "0 0 8px", fontSize: 14 }}>
                    <strong>Matched ingredients ({item.match_count ?? 0}):</strong>{" "}
                    {matched.length > 0 ? matched.join(", ") : "—"}
                  </p>
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <button
                      type="button"
                      onClick={() => handleOpenDetail(url)}
                      disabled={loadingUrl === url}
                    >
                      {loadingUrl === url
                        ? "Translating detail..."
                        : detail
                        ? "English Detail Loaded"
                        : "Show Ingredients & Steps (EN)"}
                    </button>
                    {url && (
                      <a href={url} target="_blank" rel="noreferrer">
                        Original Cookpad Link
                      </a>
                    )}
                  </div>
                </div>
              </div>

              {detail && (
                <div style={{ marginTop: 14, borderTop: "1px solid #333", paddingTop: 12 }}>
                  <h3>Ingredients (EN)</h3>
                  <ul>
                    {(detail.ingredients || []).map((ing, i) => (
                      <li key={i}>{ing}</li>
                    ))}
                  </ul>

                  <h3>Steps / Instructions (EN)</h3>
                  <ol>
                    {(detail.instructions || []).map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}