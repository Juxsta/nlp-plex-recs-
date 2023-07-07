from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
import openai
import pinecone
from plexapi.server import PlexServer
from tautulli import RawAPI
from enum import Enum
from src.core.config import settings
from typing import Any, Dict

router = APIRouter()


@router.get("/get-episode-data", tags=[" "])
def sync_db():
    
    # Pinecone setup
    pinecone.init(api_key=settings.PINECONE_API_KEY, environment=settings.PINECONE_ENV)
    index_name = "media-index"
    # Create an index if it doesn't exist
    if index_name not in pinecone.list_indexes():
        pinecone.create_index(name=index_name, dimension=1536, metric='cosine', shards=1)

    # Pinecone index
    index = pinecone.Index(index_name=index_name)

    # OpenAI setup
    openai.api_key = settings.OPENAI_API_KEY

    #plex setup
    plex = PlexServer(settings.PLEX_URL, settings.PLEX_TOKEN)
    # for show in plex.library.section('TV Shows').all():
    #     # Generate description for vector embedding
    #     # Assume item is the dictionary of metadata for a show
    #     genres = ', '.join([genre['tag'] for genre in item['genres']])
    #     actors = ', '.join([role['tag'] for role in item['roles']])
    #     description = f"Show: {item['title']}, released in {item['year']}, is a {item['contentRating']} rated show in genres {genres}. It features actors {actors}. The audience rating is {item['audienceRating']}. Summary: {item['summary']}"
    #     # Use OpenAI API to generate vector - use ada v2
    #     embedding_response = openai.Embedding.create(input=description, model="text-embedding-ada-002")
            
    #     vector = embedding_response['embeddings']
    #     # Upsert vector representation to Pinecone
    #     index.upsert(items={show.ratingKey: vector})
    batch_items = []
    batch_size = 100

    for movie in plex.library.section('Movies').all():
        description_elements = []

        if movie.title: 
            description_elements.append(f"Movie: {movie.title}")

        if movie.year:
            description_elements.append(f"released in {movie.year}")

        if movie.genres:
            genres = ', '.join([genre.tag for genre in movie.genres])
            description_elements.append(f"is in genres {genres}")

        if movie.actors:
            actors = ', '.join([role.tag for role in movie.actors])
            description_elements.append(f"It features actors {actors}")

        if movie.directors:
            directors = ', '.join([director.tag for director in movie.directors])
            description_elements.append(f"Directed by {directors}")

        if hasattr(movie, 'contentRating') and movie.contentRating:
            description_elements.append(f"is a {movie.contentRating}-rated movie")

        if hasattr(movie, 'studio') and movie.studio:
            description_elements.append(f"Produced by {movie.studio}")

        if hasattr(movie, 'audienceRating') and movie.audienceRating is not None:
            if movie.audienceRating >= 8:
                sentiment = "highly rated"
            elif movie.audienceRating >= 5:
                sentiment = "moderately rated"
            else:
                sentiment = "low rated"
            description_elements.append(f"This movie is {sentiment} by the audience with a rating score of {movie.audienceRating}")

        if movie.summary:
            description_elements.append(f"Summary: {movie.summary}")

        description = ', '.join(description_elements)

        # Generate the embeddings for this description
        embedding_response = openai.Embedding.create(input=description, model="text-embedding-ada-002")
        embedding = embedding_response['data'][0]['embedding']

        # Add the embedding for this movie to our batch
        batch_items.append(pinecone.Vector(id=str(movie.ratingKey), values=embedding))

        # Once we've accumulated enough items, we upload them to Pinecone
        if len(batch_items) == batch_size:
            index.upsert(vectors=batch_items)
            batch_items = []
            
    # Don't forget to upload the final batch if it's not empty
    if batch_items:
        index.upsert(vectors=batch_items)

    # Cleaning up
    pinecone.deinit()

class ModelName(str, Enum):
    gpt_4 = "gpt-4"
    gpt_3 = "gpt-3.5-turbo"
    gpt_3_16k = "gpt-3.5-turbo-16k"
    
@router.get("/querydb", tags=["Queries"])
async def query_db(query: str,  model: ModelName) -> Dict[str, Any]:
    # Initialize Pinecone
    pinecone.init(api_key=settings.PINECONE_API_KEY, environment=settings.PINECONE_ENV)
    index_name = "media-index"
    index = pinecone.Index(index_name=index_name)

    # OpenAI setup
    openai.api_key = settings.OPENAI_API_KEY

    # Prepare the query
    xq = openai.Embedding.create(input=query, model="text-embedding-ada-002")['data'][0]['embedding']

    # Query Pinecone index
    res = index.query(queries=[xq], top_k=20).results[0].matches


    # Assuming the ids in the response are Plex movie IDs
    plex = PlexServer(settings.PLEX_URL, settings.PLEX_TOKEN)
    results_dict = []

    # For each result returned
    for match in res:
        movie_set = plex.fetchItem(int(match.id))
        for movie in movie_set:
            movie_elements = []

            if movie.title: 
                movie_elements.append(f"Movie: {movie.title}")

            if movie.year:
                movie_elements.append(f"released in {movie.year}")
                
            if movie.genres:
                genres = ', '.join([genre.tag for genre in movie.genres])
                movie_elements.append(f"is in genres {genres}")

            if movie.actors:
                actors = ', '.join([actor.tag for actor in movie.actors])
                movie_elements.append(f"Features actors: {actors}")

            if hasattr(movie, 'contentRating') and movie.contentRating:
                movie_elements.append(f"is rated: {movie.contentRating}")

            if hasattr(movie, 'audienceRating') and movie.audienceRating:
                rating = round(movie.audienceRating, 1)
                movie_elements.append(f"With the audience rating of {rating}")

            if movie.summary:
                movie_elements.append(f"Summary: {movie.summary}")

            movie_description = ', '.join(movie_elements)

            results_dict.append(movie_description) 

    # Use OpenAI to generate a response using the found movies
    # Get the titles and concatenate them into a single string
# Format results into a human-readable string
    results_string = ', '.join(results_dict[:-1]) + " and " + results_dict[-1] if results_dict else "No matching results were found."

    # Prepare AI prompt
    prompt = f"{query} \n These are the closest results for the query: {results_string}. If no results match the query, do a 'next-best' recommendation, but specify that it is not a perfect match."

    # Generate a message from the AI
    ai_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    # Grab the assistant's reply
    assistant_reply = ai_response['choices'][0]['message']['content']

    return { "response": assistant_reply}

