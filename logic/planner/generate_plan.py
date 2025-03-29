from at_queue.utils.decorators import component_method

from planning import *
from search import *
from at_queue.core.at_component import ATComponent
from at_queue.core.session import ConnectionParameters
import asyncio
import logging
import jsonpickle
import yaml
import json
import os
import time
from dotenv import load_dotenv
load_dotenv()

# Правила (или по-другому Actions) для генерации плана
action_templates = [
    {
        'name': 'Drive',
        'params': ['X', 'Y', 'Z'],
        'precond': 'At(X, Y) & PointOfMap(Z)',
        'effect': 'At(X, Z) & ~At(X, Y)',
        'domain': 'Driver(X) & PointOfMap(Y) & PointOfMap(Z)'
    },
    {
        'name': 'Park',
        'params': ['X', 'Y', 'Z'],
        'precond': 'At(X, Y) & Parking(Z)',
        'effect': 'At(X, Z) & ~At(X, Y)',
        'domain': 'Driver(X) & PointOfMap(Y) & Parking(Z)'
    }
]

goal_positions = {
    # Цели от АТ-РЕШАТЕЛЯ и Темпорального решателя
    'Driver1': 'Parking1',  # Отправить водителя 1 на парковку 1
    'Driver2': 'Parking2',
    'Driver3': 'Parking3',
    'Driver4': 'Parking3',
    'Driver5': 'Parking2',
    'Driver6': 'Parking1',
    'Driver7': 'Parking2',
}

initial_positions = {
    'Drivers':
        {
            # Начальное состояние водителя
            'Driver1': 'PointOfMap1',  # Водитель.Состояние.Маршрут1
            'Driver2': 'PointOfMap1',
            'Driver3': 'PointOfMap1',
            'Driver4': 'PointOfMap2',
            'Driver5': 'PointOfMap2',
            'Driver6': 'PointOfMap3',
            'Driver7': 'PointOfMap3',
        },
    'Parking_locations':
        {
            # Адрес парковки, т.е. конечное состояние водителя
            'Parking1':'PointOfMap1',  # Парковка1.Локация.Пушкина1
            'Parking2': 'PointOfMap2',  # Парковка2.Локация.Толстого2
            'Parking3': 'PointOfMap3',
        },
}


CONFIG_YAML = os.getenv('CONFIG_YAML')
PLANNING_BASE_PATH = os.getenv('PLANNING_BASE_PATH')
SELECTED_RULES_FILE = os.getenv('SELECTED_RULES_FILE')

with open(CONFIG_YAML, "r") as config_file:
    config = yaml.safe_load(config_file)

connection_url = config["connection"]["url"]

class StateSpacePlanning(ATComponent):
    def __init__(self, connection_parameters: ConnectionParameters, *args, **kwargs):
        super().__init__(connection_parameters, *args, **kwargs)
        self._action_base = None
        self._goal_state_mapping = None


    @property
    def planning_base(self):
        with open(PLANNING_BASE_PATH) as f:
            return json.load(f)


    # Пространство состояний для эксперимента 1
    def state_space_1(self, driver, map_point, locations, init_posit, goal_posit, action_templates):

        initial_state = ' & '.join(f'At({d}, {r})' for d, r in init_posit['Drivers'].items())
        goal_state = ' & '.join(f'At({d}, {p})' for d, p in goal_posit.items())

        domain = (
                ' & '.join(f'Driver({d})' for d in driver) + ' & ' +
                ' & '.join(f'PointOfMap({r})' for r in map_point) + ' & ' +
                ' & '.join(f'Parking({p})' for p in locations)
        )

        actions = []

        for dr in driver:
            current_map = init_posit['Drivers'][dr]
            target_location = goal_posit[dr]
            target_location_position = init_posit['Parking_locations'][target_location]
            if target_location_position is None:
                raise ValueError(f"❌ Ошибка: не найдено местоположение для {target_location}")

            for template in action_templates:
                action_name = template['name']
                if action_name == 'Drive':
                    params = [dr, current_map, target_location_position]

                    action_str = f"{action_name}({', '.join(params)})"
                    precond = (template['precond'].replace('X', dr).
                               replace('Y', current_map)
                               .replace('Z', target_location_position))
                    effect = (template['effect'].replace('X', dr)
                              .replace('Y', current_map).replace('Z', target_location_position))
                    domain_str = (template['domain'].replace('X', dr)
                                  .replace('Y', current_map)
                                  .replace('Z', target_location_position))
                else:
                    params = [dr, target_location_position, target_location]

                    action_str = f"{action_name}({', '.join(params)})"
                    precond = (template['precond'].replace('X', dr)
                               .replace('Y', target_location_position)
                               .replace('Z', target_location))
                    effect = (template['effect'].replace('X', dr)
                              .replace('Y', target_location_position)
                              .replace('Z', target_location))
                    domain_str = (template['domain'].replace('X', dr)
                                  .replace('Y', target_location_position)
                                  .replace('Z', target_location))

                actions.append(Action(action_str, precond, effect, domain_str))

        return PlanningProblem(initial_state, goal_state, actions, domain), actions


    def gen_plan(self, driver, map_point, locations, init_posit, goal_posit, act_temp):
        world_state = {'Drivers': init_posit['Drivers'].copy(),
                       'Parking_locations': init_posit['Parking_locations'].copy()}
        final_solution = []
        act_list = []

        for dr in driver:
            print(f"\n🚗 План для {dr}")

            start_time = time.time()
            target_location = goal_posit[dr]  # По сути это номер парковки

            single_driver_problem, act = self.state_space_1(
                [dr],
                map_point,
                locations,
                {'Drivers': {dr: init_posit['Drivers'][dr]},
                 'Parking_locations': {target_location: init_posit['Parking_locations'][target_location]}},
                {dr: goal_posit[dr]},
                act_temp
            )

            result = astar_search(ForwardPlan(single_driver_problem), display=True)
            if result is None:
                raise ValueError(f"❌ astar search не нашел решение для {dr}")
            sol = result.solution()
            # sol = astar_search(ForwardPlan(single_driver_problem), display=True).solution()
            sol = list(map(lambda action: Expr(action.name, *action.args), sol))

            end_time = time.time()
            elapsed_time = end_time - start_time

            print(f"Время для {dr}: {elapsed_time:.4f} секунд")

            final_solution.extend(sol)
            act_list.append(act)

            # Обновляем мир (водитель теперь на месте) - как бы для исполнительной подсистемы
            if 'Result_for_executive_subsystem' not in world_state:
                world_state['Result_for_executive_subsystem'] = {}
            world_state['Result_for_executive_subsystem'][dr] = goal_posit[dr]

            print(f'Сгенерированный план для отдельного водителя: {sol}')

        print(f'\n🌍 Наш чудесный мир: {world_state}')
        print(f'🔑 Все созданные правила (actions): {act_list}')

        return str(final_solution)


    @component_method
    def process_agent_goal(self, at_solver_goal):
        # ЭТО САМО ГЕНЕРИТСЯ
        # 1
        drivers = list(set(initial_positions['Drivers'].keys()))
        # 2
        parkings = list(set(initial_positions['Parking_locations'].keys()))
        # 3
        map_points = []
        for points in initial_positions.values():
            map_points.extend(points.values())
        map_points = list(set(map_points))
        # 4
        # actions_name = [action['name'] for action in action_templates]

        print(f'Цель: {at_solver_goal}')
        final_plan = self.gen_plan(
            drivers,
            map_points,
            parkings,
            initial_positions,
            goal_positions,
            action_templates
        )
        print(f'Generated Plan: {final_plan}')

        return final_plan


async def main():
    connection_parameters = ConnectionParameters(connection_url) # Параметры подключения к RabbitMQ
    at_planner = StateSpacePlanning(connection_parameters=connection_parameters) # Создание компонента
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




# # Этот блок входных данных определяет участников пространства состояний. Это можно подтягивать из xml (файл прогона)
# drivers = ['Driver1']
# map_points = ['PointOfMap1', 'PointOfMap2', 'PointOfMap3']
# parkings = ['Parking1', 'Parking2']
#
# # Этот блок входных данных определяет начальное состояние пространства состояний. В идеале тут тоже нужен маппинг
# # и сами значения, то есть само начальное состояние должно браться из xml (файл прогона)
# initial_positions = {
#     # Может быть для этого словаря (чтобы было честно) сделать форму ввода - то есть не тупой маппинг, а возможность
#     # инженера по знаниям вводить это словарь с помощью UI
#     'Drivers':
#         {
#             'Driver1': 'PointOfMap1', # Водитель.Состояние.Маршрут1
#         },
#     'Parking_locations':
#         {
#             'Parking1':'PointOfMap2', # Парковка1.Локация.Пушкина1
#             'Parking2': 'PointOfMap3', # Парквока2.Локация.Толстого2
#         },
# }
# # Это цель, которая должна маппиться, например
# goal_positions = {
#     'Driver1': 'Parking1',
# }
#
#
# entities = {
#     'Driver': ['D1'],
#     'PointOfMap': ['Point1', 'Point2', 'Point3'],
#     'Parking': ['P1', 'P3']
# }
#
# relations = {
#     'At': [('D1', 'Point1')],
#     'Parking_locations': [('P1', 'Point2'), ('P2', 'Point3')],
#     'Goal': [('At', 'D1', 'P3')]
# }
#
# actions = [
#     {
#         'name': 'Drive',
#         'params': ['X', 'Y', 'Z'],
#         'precond': 'At(X, Y) & PointOfMap(Z)',
#         'effect': 'At(X, Z) & ~At(X, Y)',
#         'domain': 'Driver(X) & PointOfMap(Y) & PointOfMap(Z)'
#     },
#     {
#         'name': 'Park',
#         'params': ['X', 'Y', 'Z'],
#         'precond': 'At(X, Y) & Parking(Z)',
#         'effect': 'At(X, Z) & ~At(X, Y)',
#         'domain': 'Driver(X) & PointOfMap(Y) & Parking(Z)'
#     }
# ]


    # # Пространство состояний для эксперимента 1
    # def from_to_pp_1(self, driver, map_point, park, init_posit, goal_posit):
    #     initial_state = ' & '.join(
    #         f'At({d}, {r})' for d, r in init_posit['Drivers'].items())  # Обрабатываем вложенные данные
    #     goal_state = ' & '.join(f'At({d}, {p})' for d, p in goal_posit.items())
    #
    #     domain = (
    #             ' & '.join(f'Driver({d})' for d in driver) + ' & ' +
    #             ' & '.join(f'PointOfMap({r})' for r in map_point) + ' & ' +
    #             ' & '.join(f'Parking({p})' for p in park)
    #     )
    #
    #     actions = []
    #
    #     for dr in driver:
    #         current_map = init_posit['Drivers'][dr]  # Получаем состояние водителя
    #         target_parking = goal_posit[dr]
    #         target_parking_location = init_posit['Parking_locations'][target_parking]  # Получаем местоположение парковки
    #
    #         # Действие перемещения на нужную дорогу
    #         actions.append(Action(f'Drive({dr}, {current_map}, {target_parking_location})',
    #                               precond=f'At({dr}, {current_map}) & PointOfMap({target_parking_location})',
    #                               effect=f'At({dr}, {target_parking_location}) & ~At({dr}, {current_map})',
    #                               domain=f'Driver({dr}) & PointOfMap({current_map}) & PointOfMap({target_parking_location})'))
    #
    #         # Действие парковки
    #         actions.append(Action(f'Park({dr}, {target_parking_location}, {target_parking})',
    #                               precond=f'At({dr}, {target_parking_location}) & Parking({target_parking})',
    #                               effect=f'At({dr}, {target_parking}) & ~At({dr}, {target_parking_location})',
    #                               domain=f'Driver({dr}) & PointOfMap({target_parking_location}) & Parking({target_parking})'))
    #
    #     return PlanningProblem(initial_state, goal_state, actions, domain)


    # def generate_plan(self, driver, map_point, park, init_posit, goal_posit):
    #     # ssg = StateSpaceGenerator(entities, relations, actions)
    #     # single_driver_problem = ssg.generate_state_space()
    #
    #     world_state = {'Drivers': init_posit['Drivers'].copy(),
    #                    'Parking_locations': init_posit['Parking_locations'].copy()}
    #     final_solution = []
    #
    #     for dr in driver:
    #         print(f"\n План для {dr}")
    #
    #         start_time = time.time()
    #         target_parking = goal_posit[dr]
    #
    #         single_driver_problem = self.from_to_pp_1(
    #             [dr], map_point, park,
    #             {'Drivers': {dr: init_posit['Drivers'][dr]},
    #              'Parking_locations': {target_parking: init_posit['Parking_locations'][target_parking]}},
    #             {dr: goal_posit[dr]},
    #         )
    #
    #         # Решаем задачу
    #         solution = astar_search(ForwardPlan(single_driver_problem), display=True).solution()
    #         solution = list(map(lambda action: Expr(action.name, *action.args), solution))
    #
    #         end_time = time.time()
    #         elapsed_time = end_time - start_time
    #
    #         print(f"Время для {dr}: {elapsed_time:.4f} секунд")
    #
    #         # Добавляем в общий план
    #         final_solution.extend(solution)
    #
    #         # Обновляем мир (водитель теперь припаркован) - как бы для исполнительной подсистемы
    #         if 'Result_for_executive_subsystem' not in world_state:
    #             world_state['Result_for_executive_subsystem'] = {}
    #             world_state['Result_for_executive_subsystem'][dr] = goal_posit[dr]
    #
    #         print(solution)
    #         print(f'Наш чудесный мир: {world_state}')
    #
    #     return str(final_solution)