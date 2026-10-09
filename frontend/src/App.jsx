import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Dna, Search, Sparkles, X } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''

function prettyTrait(name) {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function App() {
  const [query, setQuery] = useState('Like Interstellar, but darker and less complicated')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')

  const examples = useMemo(() => [
    'Like Interstellar, but darker and less complicated',
    'A twisty Indian mystery with dark humor',
    'Fast sci-fi with huge visuals and strong world building',
  ], [])

  useEffect(() => {
    if (!selected) return undefined

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setSelected(null)
    }

    window.addEventListener('keydown', closeOnEscape)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', closeOnEscape)
    }
  }, [selected])

  async function runSearch(searchQuery) {
    const cleanedQuery = searchQuery.trim()
    if (!cleanedQuery) return

    setLoading(true)
    setError('')

    try {
      const res = await fetch(`${API}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: cleanedQuery, limit: 6 }),
      })

      if (!res.ok) throw new Error('Search failed')
      setResponse(await res.json())
    } catch (err) {
      setError('Movie search is temporarily unavailable. Please try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  async function searchMovies(event) {
    event?.preventDefault()
    await runSearch(query)
  }

  async function findMoreLike(movie) {
    const nextQuery = `Like ${movie.title}, but show me a different movie with similar DNA`
    setQuery(nextQuery)
    setSelected(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
    await runSearch(nextQuery)
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <div className="eyebrow"><Sparkles size={16} /> MOVIE GENOME ENGINE</div>
        <h1>CineDNA</h1>
        <p>Search movies by how they feel, not just by genre.</p>

        <form onSubmit={searchMovies} className="search-box">
          <Search size={20} />
          <input
            value={query}
            aria-label="Describe the movie you want"
            placeholder="Try: a dark Indian mystery with huge plot twists"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button disabled={loading || !query.trim()}>
            {loading ? 'Analyzing…' : 'Find movies'}
          </button>
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
            <span>How we interpreted your search</span>
            <p>{response.intent.explanation}</p>
          </div>

          <div className="results-heading">
            <div>
              <span className="section-kicker">DNA MATCHES</span>
              <h2>{response.results.length} movies ranked for your vibe</h2>
            </div>
            <p>Open any result to inspect its full Movie DNA.</p>
          </div>

          <div className="movie-grid">
            {response.results.map(({ movie, score, why }, index) => (
              <article className="movie-card" key={movie.title}>
                <div className="rank">#{index + 1}</div>
                <div className="score">{score}% match</div>
                <div className="movie-card-mark"><Dna size={18} /></div>
                <h2>{movie.title}</h2>
                <div className="meta">{movie.year} · {movie.country} · {movie.genres.join(' / ')}</div>
                <p>{movie.summary}</p>
                <p className="why">{why}</p>
                <div className="traits">
                  {Object.entries(movie.dimensions)
                    .sort((a, b) => b[1] - a[1])
                    .slice(0, 4)
                    .map(([name, value]) => (
                      <span key={name}>{prettyTrait(name)} {value}</span>
                    ))}
                </div>
                <button className="profile-button" onClick={() => setSelected({ movie, score, why })}>
                  View full DNA <ArrowRight size={16} />
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      {selected && (
        <div
          className="profile-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setSelected(null)
          }}
        >
          <section
            className="profile-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="movie-dna-title"
          >
            <button className="profile-close" aria-label="Close Movie DNA profile" onClick={() => setSelected(null)}>
              <X size={20} />
            </button>

            <div className="profile-topline">
              <div className="profile-icon"><Dna size={24} /></div>
              <div>
                <span>MOVIE DNA PROFILE</span>
                <strong>{selected.score}% match to your search</strong>
              </div>
            </div>

            <div className="profile-title-row">
              <div>
                <h2 id="movie-dna-title">{selected.movie.title}</h2>
                <p className="meta">
                  {selected.movie.year} · {selected.movie.country} · {selected.movie.genres.join(' / ')}
                </p>
              </div>
            </div>

            <p className="profile-summary">{selected.movie.summary}</p>
            <p className="profile-why">{selected.why}</p>

            <div className="theme-row">
              {selected.movie.themes.map((theme) => (
                <span key={theme}>{theme}</span>
              ))}
            </div>

            <div className="dna-grid">
              {Object.entries(selected.movie.dimensions)
                .sort((a, b) => b[1] - a[1])
                .map(([name, value]) => (
                  <div className="dna-trait" key={name}>
                    <div className="dna-trait-label">
                      <span>{prettyTrait(name)}</span>
                      <strong>{value}</strong>
                    </div>
                    <div className="dna-track" aria-label={`${prettyTrait(name)}: ${value} out of 100`}>
                      <div className="dna-fill" style={{ width: `${value}%` }} />
                    </div>
                  </div>
                ))}
            </div>

            <button className="similar-button" onClick={() => findMoreLike(selected.movie)}>
              Find more like {selected.movie.title} <ArrowRight size={17} />
            </button>
          </section>
        </div>
      )}
    </main>
  )
}

export default App
