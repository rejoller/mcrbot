from aiogram import Router, F




def setup_routers() -> Router:
    from callbacks import espd, schools
    from callbacks.survey import survey_tele2, survey_beeline, survey_mts, survey_megafon
    from handlers import (start_command, city_searcher, waiting_for_number, 
                          users_coordinates, user_phone_number,
                            help_command, vacation_file, vacation_response)
    
    router = Router()

    router.include_router(start_command.router)
    router.include_router(vacation_response.router)
    router.include_router(city_searcher.router)
    router.include_router(waiting_for_number.router)
    router.include_router(users_coordinates.router)
    router.include_router(espd.router)
    router.include_router(schools.router)
    router.include_router(user_phone_number.router)
    router.include_router(survey_tele2.router)
    router.include_router(survey_beeline.router)
    router.include_router(survey_mts.router)
    router.include_router(survey_megafon.router)
    router.include_router(help_command.router)
    router.include_router(vacation_file.router)
    

    return router