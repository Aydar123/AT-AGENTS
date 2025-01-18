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

# import sys
# sys.path.append('../..')

# import sys
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
# from data import create_action_base


with open("./package/src/config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

connection_url = config["connection"]["url"]

class ATAgentPlanner(ATComponent):
    def __init__(self, connection_parameters: ConnectionParameters, *args, **kwargs):
        super().__init__(connection_parameters, *args, **kwargs)
        self._action_base = None
        self._goal_state_mapping = None

    @property
    def planning_base(self):
        with open('./package/src/planning_base/planning_base.json') as f:
            return json.load(f)

    def create_action_base(self, planning_base):
        action_base = []
        seen_go_actions = set()

        for hla, precond, effect in zip(planning_base['HLA'], planning_base['precond'], planning_base['effect']):
            if hla.startswith("Go("):  # Проверяем, начинается ли HLA с "Go("
                if hla not in seen_go_actions:  # Проверяем, добавляли ли уже такой Go(...)
                    action = HLA(hla, precond=precond[0], effect=effect[0])
                    action_base.append(action)
                    seen_go_actions.add(hla)  # Отмечаем Go(...) как добавленный

        return action_base

    # def initialize_action_base_and_goals(self):
    #     # Инициализация базы действий
    #     self._action_base = self.create_action_base(self.planning_base)
    #
    #     # Создание списков начальных и целевых состояний
    #     initial_states = [action.precond for action in self._action_base]
    #     target_states = [action.effect for action in self._action_base]
    #
    #     # Распределение действий
    #     go_Parking, go_Alternative_Parking = self._action_base[:2]
    #     initial_state_0, target_state_0 = initial_states[0], target_states[0]
    #     initial_state_1, target_state_1 = initial_states[1], target_states[1]
    #
    #     # Создание словаря целей
    #     self._goal_state_mapping = {
    #         'Отправить_на_парковку': {
    #             'goal': go_Parking,
    #             'initial_state': initial_state_0,
    #             'target_state': target_state_0
    #         },
    #         'Отправить_на_альтернативную_парковку': {
    #             'goal': go_Alternative_Parking,
    #             'initial_state': initial_state_1,
    #             'target_state': target_state_1
    #         },
    #     }

    def initialize_action_base_and_goals(self):
        self._action_base = self.create_action_base(self.planning_base)

        # Получение начальных и целевых состояний из базы действий
        initial_states = [action.precond for action in self._action_base]
        target_states = [action.effect for action in self._action_base]
        # goal_states = [a.action for a in self._action_base]

        with open('./package/src/agents_config/selected_rules.json') as f:
            selected_rules = json.load(f)

        # Динамическое создание словаря целей
        goal_state_mapping = {}
        for idx, (rule_name, rule_data) in enumerate(selected_rules.items()):
            # Извлечение значения "value" из "assign", учитывая, что это может быть список
            assign_data = rule_data.get("action", {}).get("assign", [])
            if isinstance(assign_data, list):
                goal_values = [item.get("value") for item in assign_data if isinstance(item, dict)]
            else:
                goal_values = [assign_data.get("value")] if isinstance(assign_data, dict) else []

            # Используем начальные и целевые состояния из action_base
            initial_state = initial_states[idx] if idx < len(initial_states) else None
            target_state = target_states[idx] if idx < len(target_states) else None
            # goal_state = goal_states[idx] if idx < len(goal_states) else None

            # Находим соответствующее действие в action_base
            if idx < len(self._action_base):
                for goal_value in goal_values:
                    goal_state_mapping[goal_value] = {
                        "goal": self._action_base[idx],  # Действие из action_base
                        "initial_state": initial_state,
                        "target_state": target_state,
                    }

        self._goal_state_mapping = goal_state_mapping

        # output_file = './package/src/agents_config/goal_state_mapping.json'
        # with open(output_file, 'w', encoding='utf-8') as f:
        #     json.dump(self._goal_state_mapping, f, ensure_ascii=False, indent=2)

    @property
    def goal_state_mapping(self):
        # Ленивая инициализация словаря целей
        if self._goal_state_mapping is None:
            self.initialize_action_base_and_goals()
        return self._goal_state_mapping

    def map_goal_to_states(self, at_solver_goal):
        # Используем словарь целей для получения информации
        if at_solver_goal in self.goal_state_mapping:
            goal_info = self.goal_state_mapping[at_solver_goal]
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
    at_planner = ATAgentPlanner(connection_parameters=connection_parameters) # Создание компонента
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
