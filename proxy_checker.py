import requests
import time
import ipaddress
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from typing import List, Dict, Tuple, Any, Optional
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Константы
SUPPORTED_PROXY_TYPES = ["http", "https", "socks4", "socks5"]
DEFAULT_TIMEOUT = 10
DEFAULT_MAX_WORKERS = 30  # Снижено для стабильности
MIN_PORT, MAX_PORT = 1, 65535
TARGET_URL = "https://www.avito.ru/"


def validate_ip_address(ip: str) -> bool:
    """Валидация IP-адреса"""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def validate_port(port: str) -> bool:
    """Валидация порта"""
    try:
        port_int = int(port)
        return MIN_PORT <= port_int <= MAX_PORT
    except ValueError:
        return False


def check_proxy(proxy: str, proxy_type: str = "http", timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """
    Проверяет один прокси на работу с Avito
    
    Args:
        proxy: Прокси в формате ip:port
        proxy_type: Тип прокси (http, https, socks4, socks5)
        timeout: Таймаут соединения в секундах
        
    Returns:
        Словарь с результатами проверки
    """
    if not proxy or not isinstance(proxy, str):
        return {
            "proxy": proxy, 
            "working": False, 
            "type": proxy_type, 
            "error": "Invalid proxy format"
        }
    
    # Валидация формата прокси
    try:
        ip, port = proxy.split(":", 1)
        if not validate_ip_address(ip) or not validate_port(port):
            return {
                "proxy": proxy,
                "working": False,
                "type": proxy_type,
                "error": "Invalid IP address or port"
            }
    except ValueError:
        return {
            "proxy": proxy,
            "working": False,
            "type": proxy_type,
            "error": "Invalid proxy format (expected ip:port)"
        }
    
    start_time = time.time()
    
    # Используем контекстный менеджер для автоматического закрытия сессии
    with requests.Session() as session:
        try:
            # Настройка прокси с правильными протоколами
            proxy_type = proxy_type.lower()
            if proxy_type not in SUPPORTED_PROXY_TYPES:
                return {
                    "proxy": proxy,
                    "working": False,
                    "type": proxy_type,
                    "error": f"Unsupported proxy type: {proxy_type}"
                }
            
            if proxy_type in ["http", "https"]:
                proxies = {
                    "http": f"http://{proxy}",
                    "https": f"http://{proxy}"
                }
            elif proxy_type == "socks4":
                proxies = {
                    "http": f"socks4://{proxy}",
                    "https": f"socks4://{proxy}"
                }
            elif proxy_type == "socks5":
                proxies = {
                    "http": f"socks5://{proxy}",
                    "https": f"socks5://{proxy}"
                }
            
            session.proxies.update(proxies)
            
            # Проверка доступа к Avito с реалистичными заголовками
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            response = session.get(
                TARGET_URL,
                timeout=timeout,
                headers=headers,
                allow_redirects=True
            )
            
            # Проверяем успешность и содержимое
            if response.status_code == 200 and "avito" in response.text.lower():
                response_time = round(time.time() - start_time, 2)
                
                return {
                    "proxy": proxy,
                    "working": True,
                    "time": response_time,
                    "type": proxy_type,
                    "status": response.status_code,
                    "content_length": len(response.content)
                }
            else:
                return {
                    "proxy": proxy,
                    "working": False,
                    "type": proxy_type,
                    "error": f"HTTP {response.status_code} or invalid content"
                }
                
        except requests.exceptions.Timeout:
            return {"proxy": proxy, "working": False, "type": proxy_type, "error": "Timeout"}
        except requests.exceptions.ProxyError:
            return {"proxy": proxy, "working": False, "type": proxy_type, "error": "Proxy connection failed"}
        except requests.exceptions.ConnectionError:
            return {"proxy": proxy, "working": False, "type": proxy_type, "error": "Connection error"}
        except Exception as e:
            logger.warning(f"Unexpected error for proxy {proxy}: {e}")
            return {"proxy": proxy, "working": False, "type": proxy_type, "error": str(e)}


def load_proxies(filename: str = "proxy_list.txt") -> List[Tuple[str, str]]:
    """
    Загружает прокси из файла с валидацией
    
    Args:
        filename: Путь к файлу с прокси
        
    Returns:
        Список кортежей (proxy, type)
    """
    proxies = []
    file_path = Path(filename)
    
    if not file_path.exists():
        logger.error(f"Файл {filename} не найден!")
        return proxies
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                try:
                    parts = line.split(":")
                    if len(parts) < 2:
                        logger.warning(f"Строка {line_num}: неверный формат '{line}'")
                        continue
                    
                    # Валидация IP и порта
                    ip = parts[0].strip()
                    port = parts[1].strip()
                    
                    if not validate_ip_address(ip):
                        logger.warning(f"Строка {line_num}: неверный IP-адрес {ip}")
                        continue
                    
                    if not validate_port(port):
                        logger.warning(f"Строка {line_num}: неверный порт {port}")
                        continue
                    
                    proxy = f"{ip}:{port}"
                    proxy_type = parts[2].lower() if len(parts) > 2 else "http"
                    
                    # Валидация типа прокси
                    if proxy_type not in SUPPORTED_PROXY_TYPES:
                        logger.warning(f"Строка {line_num}: неподдерживаемый тип '{proxy_type}', используется 'http'")
                        proxy_type = "http"
                    
                    proxies.append((proxy, proxy_type))
                    
                except Exception as e:
                    logger.error(f"Строка {line_num}: ошибка обработки '{line}' - {e}")
                    
    except UnicodeDecodeError:
        logger.error(f"Ошибка кодировки файла {filename}. Используйте UTF-8.")
    except Exception as e:
        logger.error(f"Ошибка чтения файла {filename}: {e}")
    
    logger.info(f"Загружено {len(proxies)} валидных прокси")
    return proxies


def check_all_proxies(
    proxies: List[Tuple[str, str]], 
    max_workers: int = DEFAULT_MAX_WORKERS, 
    timeout: int = DEFAULT_TIMEOUT
) -> List[Dict[str, Any]]:
    """
    Проверяет все прокси параллельно с ограничением ресурсов
    
    Args:
        proxies: Список кортежей (proxy, type)
        max_workers: Максимальное количество потоков
        timeout: Таймаут для каждого прокси
        
    Returns:
        Список результатов проверки
    """
    if not proxies:
        logger.warning("Нет прокси для проверки!")
        return []
    
    # Ограничиваем количество потоков для стабильности
    max_workers = min(max_workers, len(proxies), 50)
    results = []
    total = len(proxies)
    completed = 0
    
    logger.info(f"Проверяем {total} прокси с {max_workers} потоками...")
    print("-" * 50)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_proxy, proxy, ptype, timeout): (proxy, ptype) 
            for proxy, ptype in proxies
        }
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                completed += 1
                
                status = "✓" if result["working"] else "✗"
                time_info = (
                    f"{result.get('time', 'N/A')}s" 
                    if result["working"] 
                    else result.get('error', 'failed')
                )
                progress = f"[{completed}/{total}]"
                
                print(f"{progress} {status} {result['proxy']} ({time_info})")
                
            except Exception as e:
                logger.error(f"Ошибка обработки результата: {e}")
                completed += 1
    
    return results


def save_working_proxies(
    results: List[Dict[str, Any]], 
    filename: str = "working_proxies.txt"
) -> List[Dict[str, Any]]:
    """
    Сохраняет рабочие прокси с дополнительной информацией
    
    Args:
        results: Список результатов проверки
        filename: Имя файла для сохранения
        
    Returns:
        Список рабочих прокси
    """
    if not results:
        logger.warning("Нет результатов для сохранения!")
        return []
    
    working = [r for r in results if r["working"]]
    working.sort(key=lambda x: x.get("time", 999))
    
    try:
        file_path = Path(filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"=== РЕЗУЛЬТАТЫ ПРОВЕРКИ ПРОКСИ ДЛЯ AVITO ===\n")
            f.write(f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Рабочие прокси: {len(working)} из {len(results)}\n")
            f.write(f"Успешность: {len(working)/len(results)*100:.1f}%\n\n")
            
            # Статистика по типам
            type_stats = {}
            for proxy in working:
                ptype = proxy['type']
                type_stats[ptype] = type_stats.get(ptype, 0) + 1
            
            f.write("Статистика по типам:\n")
            for ptype, count in sorted(type_stats.items()):
                f.write(f"  {ptype.upper()}: {count}\n")
            f.write("\n")
            
            f.write("=== РАБОЧИЕ ПРОКСИ ДЛЯ AVITO ===\n")
            for proxy in working:
                content_size = proxy.get('content_length', 'N/A')
                f.write(f"{proxy['proxy']} | {proxy['type']} | {proxy['time']}s | {content_size} bytes\n")
            
            # Добавляем раздел с конфигом для использования в коде
            f.write("\n=== КОНФИГ ДЛЯ ИСПОЛЬЗОВАНИЯ В КОДЕ ===\n")
            f.write("PROXY_LIST = [\n")
            for proxy in working:
                f.write(f"    {{'server': '{proxy['proxy']}', 'protocol': '{proxy['type']}'}},\n")
            f.write("]\n")
        
        logger.info(f"Результаты сохранены в {filename}")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения файла {filename}: {e}")
    
    return working


def main() -> None:
    """Основная функция"""
    print("=== ПРОКСИ ЧЕКЕР ДЛЯ AVITO ===")
    
    # Загружаем прокси
    proxies = load_proxies("proxy_list.txt")
    if not proxies:
        print("Нет прокси для проверки!")
        return
    
    print(f"Загружено {len(proxies)} прокси для проверки с Avito")
    
    # Проверяем все прокси
    results = check_all_proxies(proxies, max_workers=DEFAULT_MAX_WORKERS, timeout=DEFAULT_TIMEOUT)
    
    if not results:
        print("Не удалось получить результаты проверки!")
        return
    
    # Сохраняем результаты
    working = save_working_proxies(results)
    
    # Статистика
    print("-" * 50)
    print("ИТОГОВАЯ СТАТИСТИКА:")
    print(f"Всего проверено: {len(results)}")
    print(f"Рабочих: {len(working)}")
    print(f"Успешность: {len(working)/len(results)*100:.1f}%")
    
    if working:
        fastest = working[0]
        print(f"Самый быстрый: {fastest['proxy']} ({fastest['time']}s)")
        
        # Статистика по типам
        type_stats = {}
        for proxy in working:
            ptype = proxy['type']
            type_stats[ptype] = type_stats.get(ptype, 0) + 1
        
        print("\nПо типам:")
        for ptype, count in sorted(type_stats.items()):
            print(f"  {ptype.upper()}: {count}")


if __name__ == "__main__":
    main()
