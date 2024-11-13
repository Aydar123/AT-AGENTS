from at_queue.utils.decorators import component_method

from planning import *
from at_queue.core.at_component import ATComponent
from at_queue.core.session import ConnectionParameters
import asyncio
import logging
import jsonpickle
import yaml
import json
import os


with open("./package/src/config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

connection_url = config["connection"]["url"]

# База Планов
# База планов описана с помощью языка планирования PDDL (Planning Domain Definition Language)
planning_base = {
    'HLA': ['Go(Home, Parking)', 'Go(Home, Alternative_Parking)',
            'Driver1(Home, R1_start)', 'Driver1(R1_start, R1_finish)', 'Driver1(R1_finish, Queue)',
            'Driver1(Queue, EnterParking)', 'Driver1(EnterParking, IncreaseCounter)',
            'Driver1(IncreaseCounter, Parking)',

            'Driver2(Home, R1_start)', 'Driver2(R1_start, R1_finish)', 'Driver2(R1_finish, R2_start)',
            'Driver2(R2_start, R2_finish)', 'Driver2(R2_finish, Queue)',
            'Driver2(Queue, EnterParking)', 'Driver2(EnterParking, IncreaseCounter)',
            'Driver2(IncreaseCounter, Alternative_Parking)',
            ],

    'steps': [
        # План для Go(Home, Parking)
        ['Driver1(Home, R1_start)', 'Driver1(R1_start, R1_finish)', 'Driver1(R1_finish, Queue)',
         'Driver1(Queue, EnterParking)', 'Driver1(EnterParking, IncreaseCounter)', 'Driver1(IncreaseCounter, Parking)'],
        # План для Go(Home, Alternative_Parking)
        ['Driver2(Home, R1_start)', 'Driver2(R1_start, R1_finish)', 'Driver2(R1_finish, R2_start)',
         'Driver2(R2_start, R2_finish)', 'Driver2(R2_finish, Queue)',
         'Driver2(Queue, EnterParking)', 'Driver2(EnterParking, IncreaseCounter)',
         'Driver2(IncreaseCounter, Alternative_Parking)'],
        [], [], [], [], [], [], [], [], [], [], [], [], [], []
        ],

    'precond': [
        # Предусловия для Go(Home, Parking)
        ['At(Home) & Have(Car)'],  # Go(Home, Parking)
        ['At(Home) & Have(Car)'],  # Go(Home, Alternative_Parking)
        ['At(Home)'],  # Driver1(Home, R1_start)'
        ['At(R1_start)'],  # Driver1(R1_start, R1_finish)
        ['At(R1_finish)'],  # Driver1(R1_finish, Queue)
        ['At(Queue)'],  # Driver1(Queue, EnterParking)
        ['At(EnterParking)'],  # Driver1(EnterParking, IncreaseCounter)
        ['At(IncreaseCounter)'],  # Driver1(IncreaseCounter, Parking)

        # Предусловия для Go(Home, Alternative_Parking)
        ['At(Home)'],  # Driver2(Home, R1_start)'
        ['At(R1_start)'],  # Driver2(R1_start, R1_finish)
        ['At(R1_finish)'],  # Driver2(R1_finish, R2_start)
        ['At(R2_start)'],  # Driver2(R2_start, R2_finish)
        ['At(R2_finish)'],  # Driver2(R2_finish, Queue)
        ['At(Queue)'],  # Driver2(Queue, EnterParking)
        ['At(EnterParking)'],  # Driver2(EnterParking, IncreaseCounter)
        ['At(IncreaseCounter)'],  # Driver2(IncreaseCounter, Alternative_Parking)
    ],

    'effect': [
        # Эффекты для Go(Home, Parking)
        ['At(Parking) & ~At(Home)'],
        ['At(Alternative_Parking) & ~At(Home)'],
        ['At(R1_start) & ~At(Home)'],  # Driver1(Home, R1_start)
        ['At(R1_finish) & ~At(R1_start)'],  # Driver1(R1_start, R1_finish)
        ['At(Queue) & ~At(R1_finish)'],  # Driver1(R1_finish, Queue)
        ['At(EnterParking) & ~At(Queue)'],  # Driver1(Queue, EnterParking)
        ['At(IncreaseCounter) & ~At(EnterParking)'],  # Driver1(EnterParking, IncreaseCounter)
        ['At(Parking) & ~At(IncreaseCounter)'],  # Driver1(IncreaseCounter, Parking)

        # Эффекты для Go(Home, Alternative_Parking)
        ['At(R1_start) & ~At(Home)'],  # Driver2(Home, R1_start)
        ['At(R1_finish) & ~At(R1_start)'],  # Driver2(R1_start, R1_finish)
        ['At(R2_start) & ~At(R1_finish)'],  # Driver2(R1_finish, R2_start)
        ['At(R2_finish) & ~At(R2_start)'],  # Driver2(R2_start, R2_finish)
        ['At(Queue) & ~At(R2_finish)'],  # Driver2(R2_finish, Queue)
        ['At(EnterParking) & ~At(Queue)'],  # Driver2(Queue, EnterParking)
        ['At(IncreaseCounter) & ~At(EnterParking)'],  # Driver2(EnterParking, IncreaseCounter)
        ['At(Alternative_Parking) & ~At(IncreaseCounter)']  # Driver2(IncreaseCounter, Alternative_Parking)
    ]
}

# База Действий
go_Parking = HLA('Go(Home, Parking)', precond='At(Home)', effect='At(Parking) & ~At(Home)')
go_Alternative_Parking = HLA('Go(Home, Alternative_Parking)', precond='At(Home)',
                             effect='At(Alternative_Parking) & ~At(Home)')

# # Сериализация объектов HLA в формат JSON
# go_parking_json = go_Parking.to_json()
# go_alternative_parking_json = go_Alternative_Parking.to_json()

# Словарь целей и их соответствующих состояний
goal_state_mapping = {
    'Отправить_на_парковку': {
        'goal': go_Parking,
        'initial_state': 'At(Home) & Have(Car)',
        'target_state': 'At(Parking)'
    },
    'Отправить_на_альтернативную_парковку': {
        'goal': go_Alternative_Parking,
        'initial_state': 'At(Home) & Have(Car)',
        'target_state': 'At(Alternative_Parking)'
    },
}

class ATAgentPlanner(ATComponent):
    # def __init__(self, planning_base):
    #     self.planning_base = planning_base
    def __init__(self, connection_parameters: ConnectionParameters, planning_base, *args, **kwargs):
        # Вызов конструктора базового класса с передачей параметров
        super().__init__(connection_parameters, *args, **kwargs)
        # Инициализация базы планов
        self.planning_base = planning_base

    # Функция для определения состояния на основе цели
    def map_goal_to_states(self, at_solver_goal):
        if at_solver_goal in goal_state_mapping:
            goal_info = goal_state_mapping[at_solver_goal]
            return goal_info['goal'], goal_info['initial_state'], goal_info['target_state']
        else:
            raise ValueError(f'Неизвестная цель: {at_solver_goal}')

    def format_decomposed_goal(self, decomposed_goal_list):
        # Проверяем, что входные данные — это список
        if not isinstance(decomposed_goal_list, list):
            return "Ошибка: Ожидался список шагов, получен другой формат."

        formatted_steps = []
        for step in decomposed_goal_list:
            # Проверяем, что каждый шаг — это словарь с ключом "py/object"
            if isinstance(step, dict) and "py/object" in step:
                step_info = f"Водителю: {step['name']}"  # Извлекаем водителя
                op_args = step.get("args", {}).get("py/tuple", [])
                if op_args:
                    args = ", ".join(
                        [f"{arg['op']}" for arg in op_args])
                    step_info += f" необходимо: {args}"
                formatted_steps.append(step_info)
            else:
                formatted_steps.append(f"Неизвестный шаг: {step}")

        result = (f"Декомпозиция полученной цели от компонента вывода "
                  f"будет выглядеть следующим образом:\n" + "\n".join(formatted_steps))
        return result

    @component_method
    def process_agent_goal(self, at_solver_goal):
        print(f'Цель: {at_solver_goal}')
        # print('Возможные варианты достижения цели:')
        # for sequence in RealWorldPlanningProblem.refinements(goal, self.planning_base):
        #     print(sequence)
        #     print([x.__dict__ for x in sequence], '\n')

        # Определение цели, начального и целевого состояния на основе входной цели
        goal, initial_state, target_state = self.map_goal_to_states(at_solver_goal)

        # Инициализация проблемы
        problem = RealWorldPlanningProblem(initial_state, target_state, [goal])
        # План решения этой проблемы
        plan = RealWorldPlanningProblem.hierarchical_search(problem, self.planning_base)
        print(f'Декомпозированная цель будет следующей (hierarchical search): {plan}')
        # print([x.__dict__ for x in plan])

        # Использование jsonpickle для сериализации плана
        # return Class <'str'>
        serialized_plan = jsonpickle.encode(plan)
        print(f'Serialized Plan: {type(serialized_plan)}')

        # Преобразование сериализованной строки JSON в словарь
        # return Class <'list'>
        convert_plan_to_list = json.loads(serialized_plan)
        print(f'List Plan: {type(convert_plan_to_list)}')

        formatted_plan = self.format_decomposed_goal(convert_plan_to_list)
        print(f'Serialized Plan: {formatted_plan}')

        return formatted_plan


async def main():
    connection_parameters = ConnectionParameters(connection_url) # Параметры подключения к RabbitMQ
    at_planner = ATAgentPlanner(connection_parameters=connection_parameters, planning_base=planning_base) # Создание компонента
    await at_planner.initialize() # Подключение компонента к RabbitMQ
    await at_planner.register() # Отправка сообщения на регистрацию в брокер

    if not os.path.exists('/var/run/planner/'):
        os.makedirs('/var/run/planner/')

    with open('/var/run/planner/pidfile.pid', 'w') as f:
        f.write(str(os.getpid()))

    await at_planner.start() # Запуск компонента в режиме ожидания сообщений


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


# # Создание объекта планировщика
# planner = ATAgentPlanner(planning_base)
#
# # Пример использования метода process_agent_goal
# planner.process_agent_goal(go_Parking, 'At(Home) & Have(Car)', 'At(Parking)')
# planner.process_agent_goal(go_Alternative_Parking, 'At(Home) & Have(Car)', 'At(Alternative_Parking)')
