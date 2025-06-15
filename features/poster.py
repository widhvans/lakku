import aiohttp
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

async def get_poster(query: str, year: str = None):
    """
    Finds a poster by scraping IMDb with improved accuracy.
    """
    try:
        search_query = f"{query} {year}".strip() if year else query
        search_query = re.sub(r'\s+', '+', search_query)
        
        search_url = f"https://www.imdb.com/find?q={search_query}"
        headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'en-US,en;q=0.5'}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(search_url) as resp:
                if resp.status != 200: return None
                soup = BeautifulSoup(await resp.text(), 'html.parser')
                result_link_tag = soup.select_one("a.ipc-metadata-list-summary-item__t")
                if not result_link_tag or not result_link_tag.get('href'): return None
                movie_url = "https://www.imdb.com" + result_link_tag['href'].split('?')[0]

            async with session.get(movie_url) as movie_resp:
                if movie_resp.status != 200: return None
                movie_soup = BeautifulSoup(await movie_resp.text(), 'html.parser')
                
                # --- NEW, STRICTER SELECTOR ---
                # This selector targets the main poster within its specific container,
                # avoiding other images on the page like QR codes.
                img_tag = movie_soup.select_one('div[data-testid="hero-media__poster"] img.ipc-image')
                
                if img_tag and img_tag.get('src'):
                    poster_url = img_tag['src']
                    if '_V1_' in poster_url:
                        poster_url = poster_url.split('_V1_')[0] + "_V1_FMjpg_UX1000_.jpg"

                    # Verify the URL is a valid image before returning
                    try:
                        async with session.head(poster_url) as head_resp:
                            if head_resp.status == 200 and 'image' in head_resp.headers.get('Content-Type', ''):
                                logger.info(f"Successfully found and verified poster for '{query}'")
                                return poster_url
                    except Exception:
                        logger.warning(f"Could not verify poster URL, but returning it anyway: {poster_url}")
                        return poster_url # Return the URL even if HEAD request fails
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during poster scraping for query '{query}': {e}")
        return None
