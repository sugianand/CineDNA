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
        title="The Matrix", year=1999, country="USA",
        genres=["Science Fiction", "Action"],
        themes=["reality", "identity", "freedom", "choice", "technology", "rebellion"],
        dimensions={
            "emotional_intensity": 82, "narrative_complexity": 87, "visual_spectacle": 93,
            "pacing": 86, "mystery": 78, "romance": 18, "darkness": 75,
            "humor": 22, "plot_twists": 89, "action": 94, "character_depth": 82,
            "world_building": 96, "dialogue_density": 66, "rewatchability": 98,
        },
        summary="A landmark science-fiction action story about reality, identity, free will, and rebellion against a machine-controlled world."
    ),
    MovieDNA(
        title="The Godfather", year=1972, country="USA",
        genres=["Crime", "Drama"],
        themes=["family", "power", "loyalty", "crime", "morality", "betrayal"],
        dimensions={
            "emotional_intensity": 88, "narrative_complexity": 84, "visual_spectacle": 70,
            "pacing": 54, "mystery": 48, "romance": 12, "darkness": 88,
            "humor": 13, "plot_twists": 75, "action": 38, "character_depth": 99,
            "world_building": 86, "dialogue_density": 91, "rewatchability": 97,
        },
        summary="A landmark crime drama about family, loyalty, power, and the moral transformation of a reluctant heir."
    ),
    MovieDNA(
        title="2001: A Space Odyssey", year=1968, country="USA",
        genres=["Science Fiction", "Adventure", "Mystery"],
        themes=["space", "evolution", "technology", "humanity", "identity", "survival"],
        dimensions={
            "emotional_intensity": 58, "narrative_complexity": 94, "visual_spectacle": 98,
            "pacing": 32, "mystery": 93, "romance": 0, "darkness": 66,
            "humor": 4, "plot_twists": 82, "action": 28, "character_depth": 62,
            "world_building": 99, "dialogue_density": 24, "rewatchability": 91,
        },
        summary="A visionary science-fiction journey through human evolution, artificial intelligence, and the mysteries of space."
    ),
    MovieDNA(
        title="Back to the Future", year=1985, country="USA",
        genres=["Science Fiction", "Adventure", "Comedy"],
        themes=["time", "family", "friendship", "destiny", "invention", "home"],
        dimensions={
            "emotional_intensity": 72, "narrative_complexity": 70, "visual_spectacle": 82,
            "pacing": 86, "mystery": 55, "romance": 42, "darkness": 38,
            "humor": 82, "plot_twists": 78, "action": 70, "character_depth": 68,
            "world_building": 80, "dialogue_density": 62, "rewatchability": 97,
        },
        summary="A teenager stranded in 1955 must reunite his future parents and find a way home with help from an eccentric inventor."
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
        title="Parasite", year=2019, country="South Korea",
        original_title="기생충",
        genres=["Drama", "Thriller", "Comedy"],
        themes=["class", "inequality", "family", "deception", "greed", "survival"],
        dimensions={
            "emotional_intensity": 86, "narrative_complexity": 90, "visual_spectacle": 77,
            "pacing": 79, "mystery": 82, "romance": 5, "darkness": 88,
            "humor": 66, "plot_twists": 92, "action": 25, "character_depth": 94,
            "world_building": 70, "dialogue_density": 82, "rewatchability": 94,
        },
        summary="A Korean social thriller blending dark comedy, family drama, and escalating deception in a sharp examination of class inequality."
    ),
    MovieDNA(
        title="Spirited Away", year=2001, country="Japan",
        original_title="千と千尋の神隠し",
        genres=["Animation", "Fantasy", "Adventure"],
        themes=["identity", "family", "friendship", "greed", "courage", "transformation"],
        dimensions={
            "emotional_intensity": 86, "narrative_complexity": 78, "visual_spectacle": 96,
            "pacing": 68, "mystery": 79, "romance": 10, "darkness": 58,
            "humor": 54, "plot_twists": 70, "action": 48, "character_depth": 91,
            "world_building": 100, "dialogue_density": 54, "rewatchability": 98,
        },
        summary="A Japanese animated fantasy about a young girl's journey through a spirit world, blending courage, identity, friendship, and transformation."
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
        title="RRR", year=2022, country="India",
        genres=["Action", "Adventure", "Drama"],
        themes=["friendship", "freedom", "justice", "war", "sacrifice", "power"],
        dimensions={
            "emotional_intensity": 88, "narrative_complexity": 61, "visual_spectacle": 98,
            "pacing": 91, "mystery": 24, "romance": 22, "darkness": 64,
            "humor": 48, "plot_twists": 58, "action": 99, "character_depth": 80,
            "world_building": 83, "dialogue_density": 51, "rewatchability": 94,
        },
        summary="A large-scale Indian action drama about two revolutionaries whose friendship is tested by loyalty, sacrifice, and resistance to colonial rule."
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
    MovieDNA(
        title="Titanic", year=1997, country="USA",
        genres=["Drama", "Romance"],
        themes=["love", "class", "survival", "sacrifice", "tragedy", "history"],
        dimensions={
            "emotional_intensity": 95, "narrative_complexity": 55, "visual_spectacle": 94,
            "pacing": 64, "mystery": 20, "romance": 96, "darkness": 72,
            "humor": 18, "plot_twists": 45, "action": 55, "character_depth": 89,
            "world_building": 75, "dialogue_density": 68, "rewatchability": 94,
        },
        summary="An epic romance and disaster drama about class, sacrifice, and survival aboard the Titanic."
    ),
    MovieDNA(
        title="The Shawshank Redemption", year=1994, country="USA",
        genres=["Drama"],
        themes=["hope", "friendship", "freedom", "justice", "survival", "institutionalization"],
        dimensions={
            "emotional_intensity": 96, "narrative_complexity": 60, "visual_spectacle": 48,
            "pacing": 58, "mystery": 40, "romance": 5, "darkness": 68,
            "humor": 35, "plot_twists": 66, "action": 15, "character_depth": 99,
            "world_building": 65, "dialogue_density": 82, "rewatchability": 98,
        },
        summary="A deeply human prison drama about friendship, endurance, injustice, and the sustaining power of hope."
    ),
    MovieDNA(
        title="Avatar", year=2009, country="USA",
        genres=["Science Fiction", "Adventure", "Action"],
        themes=["nature", "colonialism", "identity", "belonging", "war", "love"],
        dimensions={
            "emotional_intensity": 80, "narrative_complexity": 55, "visual_spectacle": 100,
            "pacing": 82, "mystery": 45, "romance": 54, "darkness": 52,
            "humor": 20, "plot_twists": 48, "action": 93, "character_depth": 72,
            "world_building": 100, "dialogue_density": 44, "rewatchability": 93,
        },
        summary="A visually immersive science-fiction adventure about identity, ecology, love, and resistance on Pandora."
    ),
    MovieDNA(
        title="Avengers: Endgame", year=2019, country="USA",
        genres=["Action", "Adventure", "Science Fiction"],
        themes=["sacrifice", "friendship", "grief", "time", "family", "heroism"],
        dimensions={
            "emotional_intensity": 92, "narrative_complexity": 70, "visual_spectacle": 100,
            "pacing": 84, "mystery": 35, "romance": 20, "darkness": 65,
            "humor": 68, "plot_twists": 72, "action": 100, "character_depth": 82,
            "world_building": 95, "dialogue_density": 58, "rewatchability": 95,
        },
        summary="A large-scale superhero finale centered on grief, time travel, friendship, and costly sacrifice."
    ),
    MovieDNA(
        title="Dangal", year=2016, country="India", original_title="दंगल",
        genres=["Drama", "Sport", "Biography"],
        themes=["family", "ambition", "discipline", "equality", "competition", "success"],
        dimensions={
            "emotional_intensity": 95, "narrative_complexity": 62, "visual_spectacle": 55,
            "pacing": 76, "mystery": 20, "romance": 5, "darkness": 45,
            "humor": 48, "plot_twists": 38, "action": 25, "character_depth": 95,
            "world_building": 50, "dialogue_density": 78, "rewatchability": 94,
        },
        summary="An inspiring Indian sports drama about a father training his daughters to challenge convention and become champion wrestlers."
    ),
    MovieDNA(
        title="PK", year=2014, country="India",
        genres=["Comedy", "Drama", "Science Fiction"],
        themes=["religion", "humanity", "love", "truth", "identity", "society"],
        dimensions={
            "emotional_intensity": 82, "narrative_complexity": 70, "visual_spectacle": 52,
            "pacing": 79, "mystery": 58, "romance": 44, "darkness": 35,
            "humor": 92, "plot_twists": 62, "action": 12, "character_depth": 84,
            "world_building": 48, "dialogue_density": 88, "rewatchability": 95,
        },
        summary="A warm satirical comedy about an alien questioning religion, social customs, love, and what it means to be human."
    ),
    MovieDNA(
        title="Kantara", year=2022, country="India", original_title="ಕಾಂತಾರ",
        genres=["Action", "Drama", "Fantasy"],
        themes=["mythology", "nature", "tradition", "land", "power", "identity"],
        dimensions={
            "emotional_intensity": 83, "narrative_complexity": 68, "visual_spectacle": 91,
            "pacing": 84, "mystery": 76, "romance": 25, "darkness": 75,
            "humor": 38, "plot_twists": 73, "action": 92, "character_depth": 80,
            "world_building": 95, "dialogue_density": 58, "rewatchability": 91,
        },
        summary="A Kannada action-fantasy rooted in folklore, land conflict, ritual, nature, and spiritual inheritance."
    ),
    MovieDNA(
        title="Oldboy", year=2003, country="South Korea", original_title="올드보이",
        genres=["Thriller", "Mystery", "Drama"],
        themes=["revenge", "memory", "identity", "guilt", "truth", "obsession"],
        dimensions={
            "emotional_intensity": 92, "narrative_complexity": 91, "visual_spectacle": 73,
            "pacing": 81, "mystery": 96, "romance": 20, "darkness": 100,
            "humor": 4, "plot_twists": 100, "action": 76, "character_depth": 93,
            "world_building": 55, "dialogue_density": 70, "rewatchability": 83,
        },
        summary="A brutal Korean revenge mystery driven by imprisonment, obsession, buried memory, and a devastating revelation."
    ),
    MovieDNA(
        title="Train to Busan", year=2016, country="South Korea", original_title="부산행",
        genres=["Horror", "Action", "Thriller"],
        themes=["family", "survival", "sacrifice", "fear", "humanity", "class"],
        dimensions={
            "emotional_intensity": 95, "narrative_complexity": 58, "visual_spectacle": 82,
            "pacing": 97, "mystery": 35, "romance": 6, "darkness": 88,
            "humor": 12, "plot_twists": 45, "action": 90, "character_depth": 88,
            "world_building": 72, "dialogue_density": 45, "rewatchability": 88,
        },
        summary="A relentless Korean zombie thriller that combines claustrophobic action with family drama and human sacrifice."
    ),
    MovieDNA(
        title="Your Name", year=2016, country="Japan", original_title="君の名は。",
        genres=["Animation", "Romance", "Fantasy"],
        themes=["identity", "time", "memory", "love", "destiny", "connection"],
        dimensions={
            "emotional_intensity": 94, "narrative_complexity": 88, "visual_spectacle": 98,
            "pacing": 77, "mystery": 90, "romance": 92, "darkness": 45,
            "humor": 55, "plot_twists": 93, "action": 20, "character_depth": 88,
            "world_building": 92, "dialogue_density": 62, "rewatchability": 97,
        },
        summary="A visually stunning Japanese romance about two teenagers linked across identity, memory, distance, and time."
    ),
    MovieDNA(
        title="Amélie", year=2001, country="France",
        original_title="Le Fabuleux Destin d'Amélie Poulain",
        genres=["Romance", "Comedy", "Drama"],
        themes=["love", "loneliness", "kindness", "imagination", "connection", "identity"],
        dimensions={
            "emotional_intensity": 82, "narrative_complexity": 58, "visual_spectacle": 90,
            "pacing": 72, "mystery": 45, "romance": 84, "darkness": 18,
            "humor": 86, "plot_twists": 52, "action": 5, "character_depth": 88,
            "world_building": 82, "dialogue_density": 72, "rewatchability": 96,
        },
        summary="A whimsical French romantic comedy about a shy dreamer quietly reshaping the lives of people around her."
    ),
    MovieDNA(
        title="City of God", year=2002, country="Brazil", original_title="Cidade de Deus",
        genres=["Crime", "Drama"],
        themes=["crime", "poverty", "violence", "ambition", "survival", "friendship"],
        dimensions={
            "emotional_intensity": 91, "narrative_complexity": 81, "visual_spectacle": 78,
            "pacing": 93, "mystery": 45, "romance": 8, "darkness": 96,
            "humor": 38, "plot_twists": 79, "action": 78, "character_depth": 94,
            "world_building": 90, "dialogue_density": 74, "rewatchability": 91,
        },
        summary="A kinetic Brazilian crime drama tracing friendship, ambition, violence, and survival across generations in Rio de Janeiro."
    ),
]
