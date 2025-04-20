from at_queue.core.at_component import ATComponent
from at_queue.core.session import ConnectionParameters
from at_queue.utils.decorators import component_method
import xml.etree.ElementTree as ET
import yaml
import asyncio
from typing import Dict
import logging
import json
import os
from dotenv import load_dotenv
load_dotenv()

AGENTS = json.load(open(os.getenv('AGENTS')))
RESOURCE_PARAMETERS_PATH = os.getenv('RESOURCE_PARAMETERS_PATH')
CONFIG_YAML = os.getenv('CONFIG_YAML')

logger = logging.getLogger(__name__)

with open(CONFIG_YAML, "r") as config_file:
    config = yaml.safe_load(config_file)

connection_url = config["connection"]["url"]

class InteractionComponent(ATComponent):
    current_tact = 0

    async def configure_at_blackboard(self, *args, **kwargs):
        # Проверка, что общая рабочая память доступна
        if not await self.check_external_registered('ATBlackBoard'):
            raise ReferenceError(f'Component "ATBlackBoard" is not registered')

    async def configure_at_solver(self, agent: str):
        # Проверка, что решатель доступен
        if not await self.check_external_registered('ATSolver'):
            raise ReferenceError(f'Component "ATSolver" is not registered')

        # загружаем бз в Решатель
        config = AGENTS[agent]['ATSolver']
        await self.session.send_await('ATSolver', message={
            'type': 'configurate',
            'config': config,
        }, auth_token=agent)

    async def configure_at_temporal_solver(self, agent: str):
        # Проверка, что решатель доступен
        if not await self.check_external_registered('ATTemporalSolver'):
            raise ReferenceError(f'Component "ATTemporalSolver" is not registered')

        # загружаем базу в решатель
        config = AGENTS[agent]['ATTemporalSolver']
        await self.session.send_await('ATTemporalSolver', message={
            'type': 'configurate',
            'config': config,
        }, auth_token=agent)

    async def configure_simulation_subsystem(self, agent: str):
        pass  # подсистема имитационного моделирования пока не реализована

    async def configure_agent_planner(self, agent: str):
        # Проверка, что планировщик доступен
        if not await self.check_external_registered('StateSpacePlanning'):
        # if not await self.check_external_registered('ATAgentPlanner'):
            raise ReferenceError(f'Component "StateSpacePlanning" is not registered')

    def _items_from_solver_result(self, solver_result):
        return [
            {
                'ref': key,
                'value': wm_item['content'],
                'belief': wm_item.get('non_factor', {}).get('belief'),
                'probability': wm_item.get('non_factor', {}).get('probability'),
                'accuracy': wm_item.get('non_factor', {}).get('accuracy'),
            }
            for key, wm_item in solver_result.get('wm', {}).items()
        ]

    @component_method
    async def configure_components(self, agents: Dict):
        for agent in agents:
            await self.configure_at_solver(agent)
            await self.configure_at_temporal_solver(agent)
            await self.configure_simulation_subsystem(agent)
            await self.configure_agent_planner(agent)

    def parse_simulation_results(self, xml_file):
        tree = ET.parse(xml_file)
        root = tree.getroot()

        simulation_results = []

        for resource in root.findall('Ресурс'):
            timestep = int(resource.get('Номер_такта', 0)) - 1
            while len(simulation_results) <= timestep:
                simulation_results.append([])

            for param in resource.findall('Параметр_ресурса'):
                ref = f"{resource.get('Имя_типа_ресурса')}.{param.get('Имя_параметра')}"
                value = param.text.strip()
                simulation_results[timestep].append({'ref': ref, 'value': value})

        return simulation_results


    def extract_goals(self, data, key):
        # Получаем шаги из data['trace']
        steps = data.get('trace', {}).get('steps', [])
        goals = []

        # Проходим по каждому шагу
        for step in steps:
            # Пытаемся получить значение ключа key в final_wm_state
            final_wm_state = step.get('final_wm_state', {})
            if key in final_wm_state:
                goal_content = final_wm_state[key].get('content')
                if goal_content:
                    goals.append(goal_content)

        return goals


    @component_method
    async def interact_many_times(self, agent: str):
        results_interact = []

        simulation_results = self.parse_simulation_results(RESOURCE_PARAMETERS_PATH)

        global_generated_plan = await self.exec_external_method(
            'StateSpacePlanning',
            'simple_process_agent_goal',
            {'agent': agent}
        )

        for i in simulation_results:
            # Обновление общей рабочей памяти
            await self.exec_external_method(
                'ATBlackBoard',
                'set_items',
                {'items': i},
                auth_token=agent
            )

            # обновление рабочей памяти для темпорального решателя
            await self.exec_external_method(
                'ATTemporalSolver',
                'update_wm_from_bb',
                {},
                auth_token=agent
            )

            # Запуск темпорального решателя
            temporal_result = await self.exec_external_method(
                'ATTemporalSolver',
                'process_tact',
                {},
                auth_token=agent
            )

            # Обновление общей рабочей памяти результатом работы темпорального решателя
            temporal_items = [{'ref': key, 'value': value}
                              for key, value in temporal_result.get('signified', {}).items()]
            await self.exec_external_method(
                'ATBlackBoard',
                'set_items',
                {'items': temporal_items},
                auth_token=agent
            )

            # Обновление рабочей памяти решателя
            await self.exec_external_method(
                'ATSolver',
                'update_wm_from_bb',
                {},
                auth_token=agent
            )

            # Запуск решателя
            solver_result = await self.exec_external_method(
                'ATSolver',
                'run',
                {},
                auth_token=agent
            )

            # Обновление общей рабочей памяти результатом решателя
            solver_items = self._items_from_solver_result(solver_result)

            await self.exec_external_method(
                'ATBlackBoard',
                'set_items',
                {'items': solver_items},
                auth_token=agent
            )

            logger.info(f'-------------------------АТ-Решатель-------------------------')

            logger.info(f'\nРабочая память:{solver_result}\n')
            logger.info(f'Результат решателя:')

            # напечатаем результат решателя
            for key, wm_item in solver_result.get('wm', {}).items():
                logger.info(key, wm_item)

            logger.info(f'-------------------------Планировщик-------------------------')
            # logger.info(f"{serialized_plan}")

            key = 'Цели_агента.Цель'
            decomposed_plan_array = []
            goals_array = self.extract_goals(solver_result, key)

            # Обработка каждой цели
            for goal in goals_array:
                # Отправляем цель в планировщик
                serialized_plan = await self.exec_external_method(
                    'StateSpacePlanning',
                    # 'ATAgentPlanner',
                    'process_agent_goal',
                    {'at_solver_goal': goal, 'agent': agent}
                )
                decomposed_plan_array.append(serialized_plan)
                logger.info(f'\nЦель "{goal}" отправлена в планировщик. Результат: {serialized_plan}')


            logger.info(f'\nВсе найденные цели: {goals_array}\n')
            logger.info(f'\nВсе планы: {decomposed_plan_array}\n')


            results_interact.append({
                'solver_result': solver_result,
                'temporal_result': temporal_result,
                'wm_items': solver_result.get('wm', {}),
                'goal': goals_array,
                'serialized_plan': decomposed_plan_array,
                'global_generated_plan': global_generated_plan
            })

        logger.info(f'Все результаты тактов: {results_interact}')
        return results_interact


# Пример использования компонента
async def main():
    # ------- служебная инициализация компонента --------
    # logger.info("OK 1")
    connection_parameters = ConnectionParameters(connection_url)  # Параметры подключения к RabbitMQ

    # logger.info("OK 2")

    interaction_component = InteractionComponent(connection_parameters=connection_parameters)  # Создание компонента
    await interaction_component.initialize()  # Подключение компонента к RabbitMQ
    await interaction_component.register()  # Отправка сообщения на регистрацию в брокер

    # if not os.path.exists('/var/run/interaction_component/'):
    #     os.makedirs('/var/run/interaction_component/')
    #
    # with open('/var/run/interaction_component/pidfile.pid', 'w') as f:
    #     f.write(str(os.getpid()))

    # logger.info("OK 3")

    # Запуск в режиме ожидания сообщений, не блокируя выполнение
    loop = asyncio.get_event_loop()
    task = loop.create_task(interaction_component.start())

    # ------------------------
    # ------------------------
    # ------- поехали --------
    # ------------------------
    # ------------------------

    # logger.info("OK 4")

    # конфигурирование компонентов для агентов
    await interaction_component.configure_components(agents=AGENTS)

    # logger.info("OK 5")

    # Вызов в один раз для примера для одного агента
    agent = 'agent1'
    await interaction_component.interact_many_times(agent=agent)

    # logger.info("OK 6")
    # Это можно выполнять в цикле для разных агентов и в разных моментах времени

    # Ожидание завершения
    await task

    logger.info("OK 7")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
