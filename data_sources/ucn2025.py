from config import GOSUSLUGI_URL
import aiohttp
import pandas as pd
from datetime import datetime as dt

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update


from database.models import Cities, Ucn2025


async def ucn_votes_updater(session: AsyncSession):
    async with aiohttp.ClientSession() as client_session:
        try:
            async with client_session.get(GOSUSLUGI_URL, ssl=False, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    ucn2025_df = pd.DataFrame(data['data']['items'])
                    ucn2025_df = ucn2025_df[['subject', 'votes_total']]
                    ucn2025_df.columns = [
                        'city_name_from_gosuslugi', 'number_of_votes_ucn2025']
                    for index, row in ucn2025_df.iterrows():
                        city_id_query = select(Cities.city_id) \
                            .where(Cities.city_name_from_gosuslugi == row['city_name_from_gosuslugi'])
                        city_id_result = await session.execute(city_id_query)
                        city_id = city_id_result.scalar_one_or_none()

                        update_query = (
                            update(Ucn2025)
                            .where(Ucn2025.city_name_from_gosuslugi == row['city_name_from_gosuslugi'])
                            .values(
                                city_id=city_id,
                                number_of_votes_ucn2025=row['number_of_votes_ucn2025'],
                                date_of_update_ucn2025=dt.now()
                            )
                        )
                        result = await session.execute(update_query)
                        if result.rowcount == 0:
                            insert_query = insert(Ucn2025).values(
                                city_id=city_id,
                                city_name_from_gosuslugi=row['city_name_from_gosuslugi'],
                                number_of_votes_ucn2025=row['number_of_votes_ucn2025'],
                                date_of_update_ucn2025=dt.now()
                            )
                            await session.execute(insert_query)
                    await session.commit()
                else:
                    print(f"Request failed with status code {response.status}")
        except aiohttp.ClientTimeout:
            print("Request timed out.")
        except aiohttp.ClientError as e:
            print(f"An error occurred: {e}")
