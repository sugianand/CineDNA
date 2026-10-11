from app.models import MovieDNA

MOVIES = [
    MovieDNA(
        title="Interstellar", year=2014, country="USA",
        genres=["Science Fiction", "Drama", "Adventure"],
        themes=["time", "family", "sacrifice", "survival", "space", "humanity"],
        dimensions={
            "emotional_intensity": 94, "narrative_complexity": 88, "visual_spectacle": 97,
            "pacing": 71, "mystery": 84, "romance": 45, "darkness": 66,
            "humor": 17, "plot_twists": 80, "action": 64, "character_depth": 86,
            "world_building": 95, "dialogue_density": 62, "rewatchability": 91,
        },
        summary="A grand, emotional science-fiction story about family, time, survival, and humanity's future."
    ),
    MovieDNA(
        title="Arrival", year=2016, country="USA",
        genres=["Science Fiction", "Drama", "Mystery"],
        themes=["language", "time", "grief", "communication", "humanity", "choice"],
        dimensions={
            "emotional_intensity": 88, "narrative_complexity": 86, "visual_spectacle": 78,
            "pacing": 55, "mystery": 91, "romance": 32, "darkness": 61,
            "humor": 8, "plot_twists": 93, "action": 22, "character_depth": 90,
            "world_building": 80, "dialogue_density": 77, "rewatchability": 86,
        },
        summary="A cerebral first-contact story built around language, grief, perception, and a major emotional revelation."
    ),
    MovieDNA(
        title="Inception", year=2010, country="USA",
        genres=["Science Fiction", "Thriller", "Action"],
        themes=["dreams", "memory", "guilt", "reality", "identity", "heist"],
        dimensions={
            "emotional_intensity": 79, "narrative_complexity": 96, "visual_spectacle": 95,
            "pacing": 86, "mystery": 88, "romance": 24, "darkness": 67,
            "humor": 16, "plot_twists": 90, "action": 88, "character_depth": 75,
            "world_building": 94, "dialogue_density": 78, "rewatchability": 95,
        },
        summary="A high-concept dream heist combining layered reality, emotional guilt, action, and puzzle-box storytelling."
    ),
    MovieDNA(
        title="Shutter Island", year=2010, country="USA",
        genres=["Psychological Thriller", "Mystery"],
        themes=["identity", "trauma", "memory", "guilt", "madness", "truth"],
        dimensions={
            "emotional_intensity": 82, "narrative_complexity": 89, "visual_spectacle": 66,
            "pacing": 65, "mystery": 97, "romance": 12, "darkness": 93,
            "humor": 3, "plot_twists": 98, "action": 31, "character_depth": 89,
            "world_building": 65, "dialogue_density": 72, "rewatchability": 90,
        },
        summary="A dark psychological mystery about trauma, identity, and the dangerous boundary between truth and delusion."
    ),
    MovieDNA(
        title="Prisoners", year=2013, country="USA",
        genres=["Crime", "Thriller", "Drama"],
        themes=["morality", "family", "obsession", "justice", "faith", "desperation"],
        dimensions={
            "emotional_intensity": 93, "narrative_complexity": 76, "visual_spectacle": 52,
            "pacing": 62, "mystery": 92, "romance": 2, "darkness": 98,
            "humor": 1, "plot_twists": 85, "action": 38, "character_depth": 96,
            "world_building": 41, "dialogue_density": 72, "rewatchability": 76,
        },
        summary="A morally brutal missing-person thriller driven by desperation, ambiguity, and intense performances."
    ),
    MovieDNA(
        title="Knives Out", year=2019, country="USA",
        genres=["Mystery", "Comedy", "Crime"],
        themes=["family", "class", "deception", "greed", "murder", "truth"],
        dimensions={
            "emotional_intensity": 58, "narrative_complexity": 80, "visual_spectacle": 48,
            "pacing": 78, "mystery": 93, "romance": 5, "darkness": 48,
            "humor": 78, "plot_twists": 89, "action": 18, "character_depth": 72,
            "world_building": 39, "dialogue_density": 91, "rewatchability": 88,
        },
        summary="A witty modern murder mystery with layered deception, family conflict, social satire, and sharp dialogue."
    ),
    MovieDNA(
        title="Dune: Part Two", year=2024, country="USA",
        genres=["Science Fiction", "Adventure", "Drama"],
        themes=["power", "destiny", "religion", "war", "colonialism", "love"],
        dimensions={
            "emotional_intensity": 82, "narrative_complexity": 79, "visual_spectacle": 100,
            "pacing": 83, "mystery": 61, "romance": 47, "darkness": 75,
            "humor": 8, "plot_twists": 63, "action": 91, "character_depth": 83,
            "world_building": 100, "dialogue_density": 64, "rewatchability": 94,
        },
        summary="A monumental science-fiction epic focused on power, prophecy, war, love, and political transformation."
    ),
    MovieDNA(
        title="The Dark Knight", year=2008, country="USA",
        genres=["Crime", "Action", "Drama"],
        themes=["chaos", "morality", "justice", "sacrifice", "corruption", "identity"],
        dimensions={
            "emotional_intensity": 84, "narrative_complexity": 77, "visual_spectacle": 89,
            "pacing": 91, "mystery": 58, "romance": 19, "darkness": 89,
            "humor": 12, "plot_twists": 77, "action": 94, "character_depth": 90,
            "world_building": 76, "dialogue_density": 74, "rewatchability": 98,
        },
        summary="A crime epic about chaos, justice, sacrifice, and moral compromise disguised as a superhero film."
    ),
    MovieDNA(
        title="Baahubali: The Beginning", year=2015, country="India",
        original_title="బాహుబలి: ది బిగినింగ్",
        genres=["Action", "Adventure", "Drama"],
        themes=["power", "family", "destiny", "war", "revenge", "kingdom"],
        dimensions={
            "emotional_intensity": 84, "narrative_complexity": 68, "visual_spectacle": 96,
            "pacing": 82, "mystery": 57, "romance": 41, "darkness": 61,
            "humor": 22, "plot_twists": 72, "action": 95, "character_depth": 76,
            "world_building": 94, "dialogue_density": 55, "rewatchability": 91,
        },
        summary="An epic Indian action drama about a lost heir, family loyalty, royal power, and the battle for a kingdom."
    ),
    MovieDNA(
        title="Andhadhun", year=2018, country="India",
        genres=["Thriller", "Comedy", "Crime"],
        themes=["deception", "murder", "luck", "greed", "identity", "morality"],
        dimensions={
            "emotional_intensity": 70, "narrative_complexity": 91, "visual_spectacle": 48,
            "pacing": 88, "mystery": 94, "romance": 21, "darkness": 76,
            "humor": 72, "plot_twists": 100, "action": 37, "character_depth": 72,
            "world_building": 35, "dialogue_density": 73, "rewatchability": 93,
        },
        summary="A wickedly unpredictable Indian black-comedy thriller packed with deception, murder, and constant reversals."
    ),
    MovieDNA(
        title="Drishyam", year=2015, country="India",
        genres=["Crime", "Thriller", "Drama"],
        themes=["family", "crime", "deception", "protection", "memory", "justice"],
        dimensions={
            "emotional_intensity": 86, "narrative_complexity": 87, "visual_spectacle": 33,
            "pacing": 70, "mystery": 88, "romance": 8, "darkness": 78,
            "humor": 14, "plot_twists": 94, "action": 20, "character_depth": 88,
            "world_building": 31, "dialogue_density": 74, "rewatchability": 89,
        },
        summary="A tightly constructed Indian thriller about an ordinary father using intelligence and storytelling to protect his family."
    ),
    MovieDNA(
        title="3 Idiots", year=2009, country="India",
        genres=["Comedy", "Drama"],
        themes=["friendship", "education", "pressure", "success", "creativity", "family"],
        dimensions={
            "emotional_intensity": 84, "narrative_complexity": 55, "visual_spectacle": 44,
            "pacing": 75, "mystery": 28, "romance": 35, "darkness": 34,
            "humor": 93, "plot_twists": 49, "action": 8, "character_depth": 88,
            "world_building": 36, "dialogue_density": 82, "rewatchability": 97,
        },
        summary="A heartfelt comedy-drama about friendship, education pressure, creativity, and choosing a meaningful life."
    ),
    MovieDNA(
        title="Tumbbad", year=2018, country="India",
        genres=["Horror", "Fantasy", "Drama"],
        themes=["greed", "mythology", "curse", "family", "wealth", "consequence"],
        dimensions={
            "emotional_intensity": 75, "narrative_complexity": 73, "visual_spectacle": 86,
            "pacing": 68, "mystery": 82, "romance": 8, "darkness": 98,
            "humor": 1, "plot_twists": 70, "action": 39, "character_depth": 78,
            "world_building": 94, "dialogue_density": 56, "rewatchability": 84,
        },
        summary="A visually distinctive Indian folk-horror fable about greed, mythology, inheritance, and consequence."
    ),
]
