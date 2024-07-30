from aiogram import Router, F




def setup_routers() -> Router:
    from handlers import start_command
    from handlers import city_searcher 
    from handlers import waiting_for_number
    from handlers import users_coordinates
    from handlers import user_phone_number
    from callbacks import espd
    from callbacks import schools
    from callbacks.survey import survey_tele2
    from callbacks.survey import survey_beeline
    from callbacks.survey import survey_mts
    from callbacks.survey import survey_megafon
    from handlers import help_command 

    router = Router()


    router.include_router(start_command.router)
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


    return router