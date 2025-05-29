# ProxyHunter

Fast and efficient proxy server checker for testing their availability.

## Usage

```bash
python3 proxy_checker.py
```

## Features

- Tests HTTP, HTTPS, SOCKS4 and SOCKS5 proxies
- Validates connection to websites
- Saves working proxies in convenient format
- Generates ready-to-use config for your code

## Requirements

```bash
pip3 install 'requests[socks]'
```

## Files

- proxy_list.txt - proxy list for testing
- working_proxies.txt - results with working proxies
- proxy_checker.py - main script

## Output

Get ready-to-use list in format:
```python
PROXY_LIST = [
    {'server': '79.137.202.115:63128', 'protocol': 'https'},
    {'server': '86.110.189.154:4145', 'protocol': 'socks4'},
]
```

## License

This code is distributed for free. You can do anything with it - use, modify, distribute without any restrictions.

---

## Русская версия

Быстрый и эффективный чекер прокси-серверов для проверки их работоспособности.

## Использование

```bash
python3 proxy_checker.py
```

## Что делает

- Проверяет HTTP, HTTPS, SOCKS4 и SOCKS5 прокси
- Тестирует подключение к веб-сайтам
- Сохраняет рабочие прокси в удобном формате
- Генерирует готовый конфиг для использования в коде

## Требования

```bash
pip3 install 'requests[socks]'
```

## Файлы

- proxy_list.txt - список прокси для проверки
- working_proxies.txt - результаты с рабочими прокси
- proxy_checker.py - основной скрипт

## Результат

Получите готовый список в формате:
```python
PROXY_LIST = [
    {'server': '79.137.202.115:63128', 'protocol': 'https'},
    {'server': '86.110.189.154:4145', 'protocol': 'socks4'},
]
```

## Лицензия

Этот код распространяется бесплатно. Вы можете делать с ним что угодно - использовать, изменять, распространять без каких-либо ограничений.

