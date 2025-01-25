from at_queue.core.at_component import ATComponent
from at_queue.core.session import ConnectionParameters
from at_queue.utils.decorators import component_method
import xml.etree.ElementTree as ET
import os
import yaml
import asyncio
from typing import Dict
import logging
import json

# agents = os.getenv('AGENTS')

AGENTS = json.load(open('/package/src/agents_config/AGENTS.json'))
RESOURCE_PARAMETERS_PATH = '/package/src/at_simulation_subsystem/ResourceParameters_v3_3.xml'

logger = logging.getLogger(__name__)


with open("/package/src/config.yaml", "r") as config_file:
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
        logger.info("Checking solver registered")
        if not await self.check_external_registered('ATSolver'):
            raise ReferenceError(f'Component "ATSolver" is not registered')
        logger.info('Configuring solver')
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
        if not await self.check_external_registered('ATAgentPlanner'):
            raise ReferenceError(f'Component "ATAgentPlanner" is not registered')

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
        logger.info('Configuring agents')
        for agent in agents:
            logger.info(f'Configuring agent {agent}')
            await self.configure_at_solver(agent)
            logger.info(f'{agent} solver done')
            await self.configure_at_temporal_solver(agent)
            logger.info(f'{agent} t.solver done')
            await self.configure_simulation_subsystem(agent)
            logger.info(f'{agent} simulation done')
            await self.configure_agent_planner(agent)
            logger.info(f'{agent} planner done')
            logger.info(f'Finished configuring agent {agent}')


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


    @component_method
    async def interact_once(self, agent: str):

        # Вызов подсистемы имитационного моделирования, но она пока не реализована,
        # поэтому просто используем моковые данные
        simulation_results = {
            0: [
                {'ref': 'Парковка.Процент_заполнения', 'value': '57'},
                {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_парковку'},
                {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_альтернативную_парковку'}
            ],

            1: [
                {'ref': 'Парковка.Процент_заполнения', 'value': '75'},
                {'ref': 'Альтернативная_парковка.Расстояние', 'value': '1324'},
                {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_парковку'},
                {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_альтернативную_парковку'}
            ],

            2: [
                {'ref': 'Парковка.Процент_заполнения', 'value': '27'},
                {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_парковку'},
                {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_альтернативную_парковку'}
            ],
        }

        # Обновление общей рабочей памяти
        await self.exec_external_method(
            'ATBlackBoard',
            'set_items',
            {'items': simulation_results[self.current_tact % len(simulation_results.keys())]},
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

        # пусть цели у нас хранятся в объекте Цели_Агента в его атрибуте "Цель"
        key = 'Цели_агента.Цель'
        goal_item = solver_result['wm'][key]

        goal = goal_item['content']
        logger.info(f'\nТаким образом, цель которую необходимо выполнить: {goal}\n')

        # Отправляем цель планировщику и получаем результат
        serialized_plan = await self.exec_external_method(
            'ATAgentPlanner',
            'process_agent_goal',
            {'at_solver_goal': goal, 'agent': agent}
        )

        logger.info(f'-------------------------Планировщик-------------------------')
        logger.info(f"{serialized_plan}")

        self.current_tact += 1
        logger.info(f"Текущий такт: {self.current_tact}")

        return {
            'tact': self.current_tact,
            'solver_result': solver_result,
            'wm_items': solver_result.get('wm', {}),
            'goal': goal,
            'serialized_plan': serialized_plan
        }


    @component_method
    async def interact_many_times(self, agent: str):
        results_interact = []

        simulation_results = self.parse_simulation_results(RESOURCE_PARAMETERS_PATH)

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

            # пусть цели у нас хранятся в объекте Цели_Агента в его атрибуте "Цель"
            key = 'Цели_агента.Цель'
            goal_item = solver_result['wm'][key]

            goal = goal_item['content']
            logger.info(f'\nТаким образом, цель которую необходимо выполнить: {goal}\n')

            # Отправляем цель планировщику и получаем результат
            serialized_plan = await self.exec_external_method(
                'ATAgentPlanner',
                'process_agent_goal',
                {'at_solver_goal': goal, 'agent': agent}
            )

            logger.info(f'-------------------------Планировщик-------------------------')
            logger.info(f"{serialized_plan}")

            results_interact.append({
                'solver_result': solver_result,
                'wm_items': solver_result.get('wm', {}),
                'goal': goal,
                'serialized_plan': serialized_plan
            })

        logger.info(f'Все результаты тактов: {results_interact}')
        return results_interact


# пример использования компонента
async def main():
    # ------- служебная инициализация компонента --------
    # logger.info("OK 1")
    connection_parameters = ConnectionParameters(connection_url)  # Параметры подключения к RabbitMQ

    # logger.info("OK 2")

    interaction_component = InteractionComponent(connection_parameters=connection_parameters)  # Создание компонента
    await interaction_component.initialize()  # Подключение компонента к RabbitMQ
    await interaction_component.register()  # Отправка сообщения на регистрацию в брокер

    if not os.path.exists('/var/run/interaction_component/'):
        os.makedirs('/var/run/interaction_component/')

    with open('/var/run/interaction_component/pidfile.pid', 'w') as f:
        f.write(str(os.getpid()))

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
