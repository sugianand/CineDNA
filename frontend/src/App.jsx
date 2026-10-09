import { useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowRight,
  Brain,
  Clock3,
  Dna,
  Film,
  Flame,
  Heart,
  Laugh,
  Rocket,
  Search,
  Sparkles,
  X,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || ''
const RECENT_SEARCHES_KEY = 'cinedna:recent-searches'

function prettyTrait(name) {
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function loadRecentSearches() {
  try {
    const value = JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) || '[]')
    return Array.isArray(value) ? value.filter((item) => typeof item === 'string').slice(0, 5) : []
  } catch {
    return []
  }
}

function MoviePoster({ movie, large = false }) {
  const [failed, setFailed] = useState(false)
  const canShowPoster = Boolean(movie.poster_url) && !failed
  const initials = movie.title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase()

  return (
    <div className={`movie-poster${large ? ' movie-poster-large' : ''}`}>
      {canShowPoster ? (
        <img
          src={movie.poster_url}
          alt={`${movie.title} poster`}
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="poster-fallback" aria-label={`No poster available for ${movie.title}`}>
          <Film size={large ? 42 : 30} />
          <strong>{initials || 'CD'}</strong>
          <span>CineDNA</span>
        </div>
      )}
    </div>
  )
}

function App() {
  const [query, setQuery] = useState('Like Interstellar, but darker and less complicated')
  const [mode, setMode] = useState('vibe')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [responseMode, setResponseMode] = useState('vibe')
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [catalogReady, setCatalogReady] = useState(false)
  const [recentSearches, setRecentSearches] = useState(loadRecentSearches)
  const activeSearch = useRef(null)

  const examples = useMemo(() => (
    mode === 'title'
      ? ['Baahubali', 'RRR', 'Interstellar']
      : [
          'Like Interstellar, but darker and less complicated',
          'A twisty Indian mystery with dark humor',
          'Fast sci-fi with huge visuals and strong world building',
        ]
  ), [mode])

  const discoveryPrompts = useMemo(() => [
    {
      title: 'Mind-bending',
      subtitle: 'Twists, mystery, cerebral stories',
      query: 'A mind-bending mystery with huge plot twists and complex ideas',
      icon: Brain,
    },
    {
      title: 'Indian thrillers',
      subtitle: 'Dark, tense, unpredictable',
      query: 'A dark Indian thriller with mystery, crime, and huge plot twists',
      icon: Flame,
    },
    {
      title: 'Big-screen sci-fi',
      subtitle: 'Worlds worth getting lost in',
      query: 'Epic science fiction with huge visuals, action, and strong world building',
      icon: Rocket,
    },
    {
      title: 'Emotional',
      subtitle: 'Character-first stories that hit hard',
      query: 'An emotional character-driven drama with deep relationships',
      icon: Heart,
    },
    {
      title: 'Actually funny',
      subtitle: 'Lighter, faster, rewatchable',
      query: 'A funny fast-paced comedy with high rewatchability',
      icon: Laugh,
    },
  ], [])

  useEffect(() => {
    let cancelled = false

    fetch(`${API}/api/health`)
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => {
        if (!cancelled) setCatalogReady(Boolean(body?.tmdb_enabled))
      })
      .catch(() => {
        if (!cancelled) setCatalogReady(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => () => activeSearch.current?.abort(), [])

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

  function rememberSearch(searchQuery) {
    setRecentSearches((current) => {
      const next = [searchQuery, ...current.filter((item) => item.toLowerCase() !== searchQuery.toLowerCase())].slice(0, 5)
      try {
        localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(next))
      } catch {
        // Search still works when browser storage is unavailable.
      }
      return next
    })
  }

  async function runSearch(searchQuery, searchMode = mode) {
    const cleanedQuery = searchQuery.trim().replace(/\s+/g, ' ')
    const minimumLength = searchMode === 'vibe' ? 3 : 1
    if (cleanedQuery.length < minimumLength) {
      setError(searchMode === 'vibe'
        ? 'Describe your movie vibe in at least 3 characters.'
        : 'Enter a movie title to search.')
      return
    }

    activeSearch.current?.abort()
    const controller = new AbortController()
    activeSearch.current = controller

    setQuery(cleanedQuery)
    setLoading(true)
    setError('')
    setResponse(null)

    try {
      const res = await fetch(`${API}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: cleanedQuery, limit: 6, mode: searchMode }),
        signal: controller.signal,
      })

      if (!res.ok) throw new Error('Search failed')
      const body = await res.json()
      setResponse(body)
      setResponseMode(searchMode)
      rememberSearch(cleanedQuery)
    } catch (searchError) {
      if (searchError.name !== 'AbortError') {
        setError('We could not search CineDNA right now. Try again in a moment.')
      }
    } finally {
      if (activeSearch.current === controller) {
        activeSearch.current = null
        setLoading(false)
      }
    }
  }

  async function searchMovies(event) {
    event?.preventDefault()
    await runSearch(query)
  }

  async function findMoreLike(movie) {
    const nextQuery = `Like ${movie.title}, but show me a different movie with similar DNA`
    setMode('vibe')
    setSelected(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
    await runSearch(nextQuery, 'vibe')
  }

  function chooseMode(nextMode) {
    activeSearch.current?.abort()
    activeSearch.current = null
    setLoading(false)
    setMode(nextMode)
    setResponse(null)
    setError('')
    if (nextMode === 'title') {
      setQuery('')
    } else {
      setQuery('Like Interstellar, but darker and less complicated')
    }
  }

  return (
    <main className="app-shell">
      <header className="site-header">
        <a className="brand" href="#" aria-label="CineDNA home">
          <span className="brand-mark"><Dna size={18} /></span>
          <span>CineDNA</span>
        </a>
        <nav className="top-nav" aria-label="Primary navigation">
          <a href="#discover">Discover</a>
          <a href="#how-it-works">How it works</a>
        </nav>
        <span className="catalog-pill">
          <span className={`catalog-dot ${catalogReady ? 'catalog-dot-live' : ''}`} />
          {catalogReady ? 'Expanded catalog live' : 'CineDNA catalog'}
        </span>
      </header>

      <section className="hero">
        <div className="eyebrow"><Sparkles size={16} /> MOVIE GENOME ENGINE</div>
        <h1>CineDNA</h1>
        <p>Tell us what you want to feel. We turn your words into Movie DNA and rank the closest matches.</p>

        <div className="search-mode-switch" role="tablist" aria-label="Search type">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'vibe'}
            className={mode === 'vibe' ? 'active' : ''}
            onClick={() => chooseMode('vibe')}
          >
            <Sparkles size={15} /> Describe a vibe
          </button>
          {catalogReady && (
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'title'}
              className={mode === 'title' ? 'active' : ''}
              onClick={() => chooseMode('title')}
            >
              <Film size={15} /> Find a movie
            </button>
          )}
        </div>

        <form onSubmit={searchMovies} className="search-box">
          <Search size={20} />
          <input
            value={query}
            aria-label={mode === 'title' ? 'Search for a movie title' : 'Describe the movie you want'}
            placeholder={mode === 'title' ? 'Search Baahubali, RRR, Parasite…' : 'Try: a dark Indian mystery with huge plot twists'}
            onChange={(event) => setQuery(event.target.value)}
            autoComplete="off"
            minLength={mode === 'vibe' ? 3 : 1}
          />
          <button disabled={loading || query.trim().length < (mode === 'vibe' ? 3 : 1)}>
            {loading ? 'Analyzing…' : mode === 'title' ? 'Search title' : 'Find my movie'}
          </button>
        </form>

        <div className="examples" aria-label="Example searches">
          {examples.map((example) => (
            <button key={example} onClick={() => runSearch(example)}>{example}</button>
          ))}
        </div>

        {recentSearches.length > 0 && !response && !loading && (
          <div className="recent-searches">
            <span><Clock3 size={13} /> Recent</span>
            <div>
              {recentSearches.slice(0, 3).map((item) => (
                <button key={item} onClick={() => runSearch(item)} title={item}>{item}</button>
              ))}
            </div>
          </div>
        )}

        {error && <p className="error">{error}</p>}
      </section>

      {loading && (
        <section className="results" aria-live="polite" aria-busy="true">
          <div className="loading-banner">
            <Sparkles size={18} />
            <div>
              <strong>Decoding your Movie DNA…</strong>
              <span>Comparing tone, pacing, emotion, mystery, spectacle and more.</span>
            </div>
          </div>
          <div className="movie-grid">
            {[0, 1, 2].map((item) => (
              <div className="movie-card skeleton-card" key={item} aria-hidden="true">
                <div className="skeleton skeleton-poster" />
                <div className="movie-card-body">
                  <div className="skeleton skeleton-title" />
                  <div className="skeleton skeleton-line" />
                  <div className="skeleton skeleton-line short" />
                  <div className="skeleton skeleton-tags" />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {response && !loading && (
        <section className="results">
          <div className="intent-card">
            <span>{responseMode === 'title' ? 'Title search summary' : 'How we interpreted your search'}</span>
            <p>{response.intent.explanation}</p>
          </div>

          <div className="results-heading">
            <div>
              <span className="section-kicker">
                {responseMode === 'title' ? 'TITLE RESULTS' : 'DNA MATCHES'}
              </span>
              <h2>
                {response.results.length > 0
                  ? responseMode === 'title'
                    ? `${response.results.length} title ${response.results.length === 1 ? 'match' : 'matches'}`
                    : `${response.results.length} movies ranked for your vibe`
                  : responseMode === 'title'
                    ? 'No matching title found'
                    : 'No strong matches yet'}
              </h2>
            </div>
            <button className="start-over" onClick={() => setResponse(null)}>Start a new search</button>
          </div>

          {response.results.length > 0 ? (
            <div className="movie-grid">
              {response.results.map(({ movie, score, why }, index) => (
                <article className="movie-card" key={`${movie.source || 'cinedna'}-${movie.source_id || movie.title}`}>
                  <div className="poster-shell">
                    <MoviePoster movie={movie} />
                    <div className="poster-rank">#{index + 1}</div>
                    <div className="poster-score">
                      {score}% {responseMode === 'title' ? 'title match' : 'match'}
                    </div>
                  </div>

                  <div className="movie-card-body">
                    <div className="movie-card-heading">
                      <div>
                        <h2>{movie.title}</h2>
                        <div className="meta">{movie.year || 'Year unknown'} · {movie.country} · {movie.genres.join(' / ')}</div>
                      </div>
                      <div className="movie-card-mark"><Dna size={17} /></div>
                    </div>

                    {movie.original_title && movie.original_title !== movie.title && (
                      <p className="original-title">Original title: {movie.original_title}</p>
                    )}

                    <p className="summary">{movie.summary}</p>
                    <p className="why">{why}</p>

                    <div className="traits">
                      {Object.entries(movie.dimensions)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 4)
                        .map(([name, value]) => (
                          <span key={name}>{prettyTrait(name)} {value}</span>
                        ))}
                    </div>

                    <div className="card-footer">
                      <span className="source-pill">{movie.source === 'tmdb' ? 'TMDB catalog' : 'CineDNA catalog'}</span>
                      <button className="profile-button" onClick={() => setSelected({ movie, score, why })}>
                        View full DNA <ArrowRight size={16} />
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Dna size={30} />
              <h3>
                {responseMode === 'title'
                  ? 'We could not find that movie title.'
                  : 'Try describing the feeling instead.'}
              </h3>
              <p>
                {responseMode === 'title'
                  ? 'Check the spelling, try an alternate title, or switch to vibe discovery.'
                  : 'Use a mood, genre, country, or a movie you already love and CineDNA will broaden the search.'}
              </p>
              {responseMode === 'title' ? (
                <button onClick={() => chooseMode('vibe')}>
                  Describe a vibe <ArrowRight size={15} />
                </button>
              ) : (
                <button onClick={() => runSearch('A gripping mystery with strong characters and surprising plot twists', 'vibe')}>
                  Surprise me <ArrowRight size={15} />
                </button>
              )}
            </div>
          )}
        </section>
      )}

      {!response && !loading && (
        <>
          <section className="discover-section" id="discover">
            <div className="section-heading">
              <div>
                <span className="section-kicker">DISCOVER BY FEELING</span>
                <h2>Not sure what to type?</h2>
              </div>
              <p>Pick a lane. CineDNA will do the rest.</p>
            </div>

            <div className="discovery-grid">
              {discoveryPrompts.map(({ title, subtitle, query: prompt, icon: Icon }) => (
                <button className="discovery-card" key={title} onClick={() => runSearch(prompt, 'vibe')}>
                  <span className="discovery-icon"><Icon size={21} /></span>
                  <span className="discovery-copy">
                    <strong>{title}</strong>
                    <small>{subtitle}</small>
                  </span>
                  <ArrowRight size={17} />
                </button>
              ))}
            </div>
          </section>

          <section className="how-it-works" id="how-it-works" aria-label="How CineDNA works">
            <span className="section-kicker">HOW IT WORKS</span>
            <div className="steps">
              <article><strong>01</strong><h2>Describe a vibe</h2><p>Use normal language, a movie title, a mood, or a mix of all three.</p></article>
              <article><strong>02</strong><h2>Decode the DNA</h2><p>CineDNA maps your request to traits like mystery, pacing, darkness, humor, and spectacle.</p></article>
              <article><strong>03</strong><h2>Find your match</h2><p>Explore ranked movies, inspect their DNA, then branch into more movies like them.</p></article>
            </div>
          </section>
        </>
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

            <div className="profile-hero">
              <MoviePoster key={selected.movie.source_id || selected.movie.title} movie={selected.movie} large />
              <div className="profile-copy">
                <div className="profile-topline">
                  <div className="profile-icon"><Dna size={24} /></div>
                  <div>
                    <span>MOVIE DNA PROFILE</span>
                    <strong>{selected.score}% match to your search</strong>
                  </div>
                </div>

                <div className="profile-title-row">
                  <h2 id="movie-dna-title">{selected.movie.title}</h2>
                  <p className="meta">
                    {selected.movie.year || 'Year unknown'} · {selected.movie.country} · {selected.movie.genres.join(' / ')}
                  </p>
                  {selected.movie.original_title && selected.movie.original_title !== selected.movie.title && (
                    <p className="original-title">Original title: {selected.movie.original_title}</p>
                  )}
                </div>

                <p className="profile-summary">{selected.movie.summary}</p>
                <p className="profile-why">{selected.why}</p>

                <div className="theme-row">
                  {selected.movie.themes.map((theme) => (
                    <span key={theme}>{theme}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="dna-section-heading">
              <span>FULL DNA</span>
              <p>Every trait is scored from 0 to 100.</p>
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

      <footer className="site-footer">
        <span>CineDNA · Movie discovery by feeling.</span>
        <span>Movie metadata may be supplied by TMDB. CineDNA is not endorsed or certified by TMDB.</span>
      </footer>
    </main>
  )
}

export default App
