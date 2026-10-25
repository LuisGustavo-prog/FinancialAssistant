from app.controllers import month_routine_controller
from app.controllers.month_routine_controller import RoutineResult

def run_month_routine() -> RoutineResult:
    return month_routine_controller.run()
