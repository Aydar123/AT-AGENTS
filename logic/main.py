from at_queue.core.at_component import ATComponent
from at_queue.core.session import ConnectionParameters
from at_queue.utils.decorators import component_method
import asyncio
from typing import Dict
from colorama import Fore, Style

AGENTS = {
    'agent1': {
        'ATSolver': {
            'kb': {'path': 'logic/agents_config/Kutdusov_parking_kb_v3_2.xml'}
        },
        'ATTemporalSolver': {
            'kb': {'path': 'logic/agents_config/Kutdusov_parking_kb_v3_2.xml'}
        },
        'ATSimulationSubsystem': {}
    },
    'agent2': {
        'ATSolver': {
            'kb': {'path': 'logic/agents_config/Kutdusov_parking_kb_v3_2.xml'}
        },
        'ATTemporalSolver': {
            'kb': {'path': 'logic/agents_config/Kutdusov_parking_kb_v3_2.xml'}
        },
        'ATSimulationSubsystem': {}
    },
    'agent3': {
        'ATSolver': {
            'kb': {'path': 'logic/agents_config/Kutdusov_parking_kb_v3_2.xml'}
        },
        'ATTemporalSolver': {
            'kb': {'path': 'logic/agents_config/Kutdusov_parking_kb_v3_2.xml'}
        },
        'ATSimulationSubsystem': {}
    },
}

# def pause_output():
#     input("Нажмите 'Запустить Планировщик'...")

class InteractionComponent(ATComponent):

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
    async def configure_components(self, agents: Dict) -> int:
        for agent in agents:
            await self.configure_at_solver(agent)
            await self.configure_at_temporal_solver(agent)
            await self.configure_simulation_subsystem(agent)
            await self.configure_agent_planner(agent)

    @component_method
    async def interact_once(self, agent: str):
        # Вызов подсистемы имитационного моделирования, но она пока не реализована,
        # поэтому просто используем моковые данные
        simulation_result = [
            {'ref': 'Парковка.Процент_заполнения', 'value': '27'},
            {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_парковку'},
            {'ref': 'Транспортное_средство.Состояние_тс', 'value': 'Едет_на_альтернативную_парковку'},
            # Правило 2: Отправление_Альтернативная_парковка (output: True)
            # {'ref': 'Парковка.Процент_заполнения.', 'value': '80'},
            # {'ref': 'Альтернативная_парковка.Расстояние', 'value': '1500'},
            # Правило 3: Включение_приоритета_выезда (output: True)
            # {'ref': 'Парковка.Очередь_на_въезд', 'value': '5'},
            # {'ref': 'Транспортное_средство.Приоритет_выезда_тс', 'value': 'Есть'},
        ]

        # Обновление общей рабочей памяти
        await self.exec_external_method(
            'ATBlackBoard',
            'set_items',
            {'items': simulation_result},
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

        print(f'-------------------------АТ-Решатель-------------------------')

        print(f'\nРабочая память:{solver_result}\n')
        print(f'Результат решателя:')

        # напечатаем результат решателя
        for key, wm_item in solver_result.get('wm', {}).items():
            print(key, wm_item)

        # пусть цели у нас хранятся в объекте Цели_Агента в его атрибуте "Цель"
        key = 'Цели_агента.Цель'
        goal_item = solver_result['wm'][key]

        goal = goal_item['content']
        print(f'\nТаким образом, цель которую необходимо выполнить: {goal}\n')

        # # отправляем цель планировщику
        # # пусть у планировщика будет метод process_agent_goal
        # await self.exec_external_method(
        #     'ATAgentPlanner',
        #     'process_agent_goal',
        #     {'at_solver_goal': goal, 'agent': agent}
        # )

        # Отправляем цель планировщику и получаем результат
        serialized_plan = await self.exec_external_method(
            'ATAgentPlanner',
            'process_agent_goal',
            {'at_solver_goal': goal, 'agent': agent}
        )

        # pause_output()
        print(f'-------------------------Планировщик-------------------------')
        print(f"{serialized_plan}")


# пример использования компонента
async def main():
    # ------- служебная инициализация компонента --------
    # print("OK 1")
    connection_parameters = ConnectionParameters('amqp://0.0.0.0:5672/')  # Параметры подключения к RabbitMQ

    # print("OK 2")

    interaction_component = InteractionComponent(connection_parameters=connection_parameters)  # Создание компонента
    await interaction_component.initialize()  # Подключение компонента к RabbitMQ
    await interaction_component.register()  # Отправка сообщения на регистрацию в брокер

    # print("OK 3")

    # Запуск в режиме ожидания сообщений, не блокируя выполнение
    loop = asyncio.get_event_loop()
    task = loop.create_task(interaction_component.start())

    # ------------------------
    # ------------------------
    # ------- поехали --------
    # ------------------------
    # ------------------------

    # print("OK 4")

    # конфигурирование компонентов для агентов
    await interaction_component.configure_components(agents=AGENTS)

    # print("OK 5")

    # Вызов в один раз для примера для одного агента
    agent = 'agent1'
    await interaction_component.interact_once(agent=agent)

    # print("OK 6")
    # Это можно выполнять в цикле для разных агентов и в разных моментах времени

    # Ожидание завершения
    await task

    print("OK 7")


if __name__ == '__main__':
    asyncio.run(main())
