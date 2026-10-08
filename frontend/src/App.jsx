import { useMemo, useState } from 'react'
import { Search, Sparkles } from 'lucide-react'

const API = 'http://localhost:8000'

function App() {
  const [query, setQuery] = useState('Like Interstellar, but darker and less complicated')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState('')

  const examples = useMemo(() => [
    'Like Interstellar, but darker and less complicated',
    'A twisty Indian mystery with dark humor',
    'Fast sci-fi with huge visuals and strong world building',
  ], [])

  async function searchMovies(event) {
    event?.preventDefault()
    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${API}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 6 }),
      })

      if (!res.ok) throw new Error('Search failed')
      setResponse(await res.json())
    } catch (err) {
      setError('Could not reach the CineDNA API. Make sure FastAPI is running on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="eyebrow"><Sparkles size={16} /> AI MOVIE GENOME ENGINE</div>
        <h1>CineDNA</h1>
        <p>Search movies by how they feel, not just by genre.</p>

        <form onSubmit={searchMovies} className="search-box">
          <Search size={20} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} />
          <button disabled={loading}>{loading ? 'Analyzing…' : 'Find movies'}</button>
        </form>

        <div className="examples">
          {examples.map((example) => (
            <button key={example} onClick={() => setQuery(example)}>{example}</button>
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {response && (
        <section className="results">
          <div className="intent-card">
            <span>AI interpretation</span>
            <p>{response.intent.explanation}</p>
          </div>

          <div className="movie-grid">
            {response.results.map(({ movie, score, why }, index) => (
              <article className="movie-card" key={movie.title}>
                <div className="rank">#{index + 1}</div>
                <div className="score">{score}% match</div>
                <h2>{movie.title}</h2>
                <div className="meta">{movie.year} · {movie.country} · {movie.genres.join(' / ')}</div>
                <p>{movie.summary}</p>
                <p className="why">{why}</p>
                <div className="traits">
                  {Object.entries(movie.dimensions)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 4)
                    .map(([name, value]) => (
                      <span key={name}>{name.replaceAll('_', ' ')} {value}</span>
                    ))}
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}

export default App
