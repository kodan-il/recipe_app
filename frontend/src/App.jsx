import { useState } from 'react';
import axios from 'axios';

function App() {
  const [inputIngredients, setInputIngredients] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSearch = async () => {
    if (!inputIngredients.trim()) return;
    setLoading(true);
    setErrorMsg('');

    const ingredientsList = inputIngredients
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);

    try {
      const response = await axios.post(
        'http://127.0.0.1:8000/api/recipes/by-ingredients',
        ingredientsList
      );

      console.log('API response:', response.data);

      // Tangani jika response.data berupa array langsung atau dibungkus properti tertentu
      const rawData = Array.isArray(response.data)
        ? response.data
        : Array.isArray(response.data?.results)
          ? response.data.results
          : Array.isArray(response.data?.data)
            ? response.data.data
            : [];

      setResults(rawData);
    } catch (error) {
      console.error('Error fetching recipes:', error);
      setResults([]);
      setErrorMsg('Gagal mengambil data dari server backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif', maxWidth: '600px', margin: '0 auto' }}>
      <h1>🥑 Recipe Finder App</h1>
      <p>Type the ingredients you have (use commas to separate):</p>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input
          type="text"
          placeholder="Contoh: telur, tahu, bawang"
          value={inputIngredients}
          onChange={(e) => setInputIngredients(e.target.value)}
          style={{ flex: 1, padding: '10px' }}
        />
        <button onClick={handleSearch} style={{ padding: '10px 20px', cursor: 'pointer' }}>
          {loading ? 'Searching...' : 'Find recipe'}
        </button>
      </div>

      {errorMsg && <p style={{ color: 'red' }}>{errorMsg}</p>}

      <div>
        <h2>Search Results:</h2>
        {!loading && results.length === 0 && (
          <p>No results found. Try typing "Eggs" or "Garlic".</p>
        )}

        {Array.isArray(results) &&
          results.map((item, index) => {
            const recipe = item?.recipe ?? item;
            const matched = Array.isArray(item?.matched_ingredients)
              ? item.matched_ingredients
              : [];
            const steps = Array.isArray(recipe?.instructions)
              ? recipe.instructions
              : [];

            return (
              <div
                key={recipe?.id ?? index}
                style={{
                  border: '1px solid #ccc',
                  padding: '15px',
                  borderRadius: '8px',
                  marginBottom: '10px',
                }}
              >
                <h3>{recipe?.title ?? 'Tanpa Judul'}</h3>
                {matched.length > 0 && (
                  <p>
                    <strong>Ingredients:</strong> {matched.join(', ')}
                  </p>
                )}
                <p>
                  <strong>Image:</strong>
                </p>
                <ol>
                  {steps.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ol>
              </div>
            );
          })}
      </div>
    </div>
  );
}

export default App;