# Руководство для начинающих

Этот гайд поможет запустить карточного бота за несколько шагов.

## 1. Подготовка
1. Установите Python 3.11+ (убедитесь, что добавлен в PATH).
2. Клонируйте проект CardForge или распакуйте архив в удобное место.
3. Откройте терминал в корне проекта и выполните:
   ```bash
   python -m pip install -e .[dev]
   ```

## 2. Токен и конфигурация
1. Получите токен у @BotFather и сохраните в файле .env:
   `
   CARDFORGE_BOT_TOKEN=123456:ABCDEF...
   `
2. Для тестового бота можно запустить:
   ```bash
   python local_bot/run_bot.py
   ```
   Скрипт автоматически использует SQLite local_bot/cardforge.db, поэтому инвентарь и кулдауны сохраняются.

## 3. Собственный каталог
1. Отредактируйте examples/catalog/cards.json или создайте свой каталог через cardforge-studio:
   ```bash
   cardforge-studio
   ```
2. Следуйте подсказкам студии: добавьте валюты, карты, паки, сохраните проект.

## 4. Готовый пример
examples/basic_bot.py демонстрирует:
- удалённые изображения карт;
- две мини-игры (/coinflip, /diceduel);
- inline-кнопки коллекции, мини-игр и помощи.

Запуск собственного бота:
```bash
python examples/basic_bot.py
```

## 5. Быстрая адаптация под себя
1. Скопируйте examples/basic_bot.py и обновите функцию 
egister (свои карты/мини-игры).
2. При необходимости используйте упрощённый API:
   ```python
   from cardforge.abstractions import SimpleBotConfig, run_simple_bot_sync
   from pathlib import Path

   run_simple_bot_sync(
       SimpleBotConfig(
           bot_token="123:ABC...",
           catalog_path=Path("my_catalog/cards.json"),
           default_pack="starters",
           storage="my_bot/cardforge.db",
           admin_ids=(123456789,),
       )
   )
   ```

## 6. Где искать помощь
- /help в боте выводит краткую справку и inline-кнопки.
- Документация: docs/ru/getting_started.md, docs/ru/development_guide.md.
- CLI подсказки: cardforge-validate --help, cardforge-sim --help.
