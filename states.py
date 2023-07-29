from aiogram.dispatcher.fsm.state import StatesGroup, State


class BotStates(StatesGroup):
    event_puzzles = State()
    event_puzzles_select_puzzle = State()
    event_puzzles_select_account_data = State()

    event_trader = State()
    event_trader_select_code = State()

    event_thanksgiving = State()
    event_thanksgiving_select_account_data = State()

    event_home = State()
    event_home_select_code = State()

    event_team = State()
    event_team_select_code = State()


    donate = State()
