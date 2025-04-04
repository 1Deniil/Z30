import re
import logging
import time
import requests
from lxml import html
from bs4 import BeautifulSoup

from shared.timing_utils import log_execution_time

logger = logging.getLogger('minecraft_bot.stats')

class HypixelScraper:
    """Web scraper for Hypixel player statistics from Plancke.io"""
    
    @staticmethod
    @log_execution_time("get_guild_info")
    def get_guild_info(username):
        """Gets guild information for a player"""
        url = f"https://plancke.io/hypixel/player/stats/{username}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        try:
            # HTTP request
            start_req = time.perf_counter()
            response = requests.get(url, headers=headers)
            req_time = time.perf_counter() - start_req

            if response.status_code == 404:
                return f"Ran into an error! The player '{username}' doesn't appear to exist!"

            response.raise_for_status()

            # HTML parsing
            start_parse = time.perf_counter()
            tree = html.fromstring(response.content)
            xpath = '//*[@id="wrapper"]/div[3]/div/div/div[2]/div[1]/div[1]/div/span'
            span_elements = tree.xpath(xpath)

            result_text = None
            if span_elements:
                last_span = span_elements[-1]
                result_text = last_span.text_content().strip()
                
                # Look for guild name
                h4_elements = tree.xpath('//h4[text()="Guild"]')
                if h4_elements:
                    h4_element = h4_elements[0]
                    sibling_elements = h4_element.getparent().getchildren()
                    for sibling in sibling_elements:
                        if sibling.tag == 'a':
                            guild_name = sibling.text_content().strip()
                            if guild_name.lower() == "felony":
                                guild_name += " #YUCKY"
                            result_text = f"{result_text} - {guild_name}"
                            break
            
            parse_time = time.perf_counter() - start_parse
            
            logger.info(f"Guild info request: {req_time*1000:.2f}ms, "
                        f"Parsing: {parse_time*1000:.2f}ms, "
                        f"Total: {(time.perf_counter() - start_req)*1000:.2f}ms")
            
            return result_text
        except Exception as err:
            logger.error(f"Error getting guild info: {err}")
            return None
    
    @staticmethod
    @log_execution_time("get_bedwars_stats")
    def get_bedwars_stats(username, game_mode, subcategory):
        """Gets BedWars statistics for a player"""
        url = f"https://plancke.io/hypixel/player/stats/{username}#BedWars"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        try:
            start_req = time.perf_counter()
            response = requests.get(url, headers=headers)
            req_time = time.perf_counter() - start_req

            if response.status_code == 404:
                return f"Ran into an error! The player '{username}' doesn't appear to exist!"

            response.raise_for_status()

            parse_start = time.perf_counter()
            content = response.content
            if content is None:
                logger.error("Response content is None")
                return None

            soup = BeautifulSoup(content, 'html.parser')
            parse_time = time.perf_counter() - parse_start

            stats = HypixelScraper._process_bedwars_soup(soup, username, game_mode, subcategory)

            logger.info(f"BedWars stats request: "
                        f"Request: {req_time*1000:.2f}ms, "
                        f"Parsing: {parse_time*1000:.2f}ms, "
                        f"Total: {(time.perf_counter() - start_req)*1000:.2f}ms")

            return stats
        except Exception as err:
            logger.error(f"Error getting BedWars stats: {err}")
            return None
    
    @staticmethod
    @log_execution_time("process_bedwars_soup")
    def _process_bedwars_soup(soup, username, game_mode, subcategory):
        """Processes BeautifulSoup object to extract BedWars stats"""
        # Find player level
        level_tag = None
        for li_tag in soup.find_all('li'):
            b_tag = li_tag.find('b', string=lambda string: string and 'Level:' in string)
            if b_tag:
                level_tag = b_tag
                break

        if level_tag:
            level_number = level_tag.next_sibling.strip()
            level_number = ''.join(filter(lambda x: x.isdigit() or x == '.', level_number))
        else:
            level_number = "N/A"

        if subcategory == 'lvl':
            return f"[{level_number}✫] {username}"

        # Mapping of stats to abbreviations
        stat_abbreviations = {
            'kills': 'K',
            'kd': 'KD',
            'finals': 'F',
            'fkdr': 'FKDR',
            'wins': 'W',
            'beds': 'B',
            'wlr': 'WLR',
            'bblr': 'BBLR'
        }

        # Map command to table header text
        command_to_th_text = {
            'bw 1s': 'Solo',
            'bw 2s': 'Doubles',
            'bw 3s': '3v3v3v3',
            'bw 4s': '4v4v4v4',
            'bw 4v4': '4v4',
            'bw core': 'Core Modes',
            'bw': 'Overall',
            '1s': 'Solo',
            '2s': 'Doubles',
            '3s': '3v3v3v3',
            '4s': '4v4v4v4',
            '4v4': '4v4',
            'core': 'Core Modes'
        }

        # Find the correct table row for the game mode
        th_text = command_to_th_text.get(game_mode, 'Overall')
        th_tag = soup.find('th', {'scope': 'row'}, string=th_text)
        
        if th_tag:
            tr_tag = th_tag.find_parent('tr')
            if tr_tag:
                td_tags = tr_tag.find_all('td')
                if len(td_tags) >= 10:
                    # Extract all stats
                    kills = td_tags[0].get_text(strip=True)
                    kd = td_tags[2].get_text(strip=True)
                    finals = td_tags[3].get_text(strip=True)
                    fkdr = td_tags[5].get_text(strip=True)
                    wins = td_tags[6].get_text(strip=True)
                    wlr = td_tags[8].get_text(strip=True)
                    losses = td_tags[7].get_text(strip=True)
                    beds = td_tags[9].get_text(strip=True)

                    # Calculate BBLR (Beds Broken/Lost Ratio)
                    try:
                        beds_num = float(beds.replace(',', '')) if beds != 'N/A' else 0
                        losses_num = float(losses.replace(',', '')) if losses != 'N/A' else 0
                        bblr = f"{beds_num/losses_num:.2f}" if losses_num != 0 else "N/A"
                    except:
                        bblr = "N/A"
                else:
                    kills = kd = finals = fkdr = wins = beds = wlr = losses = bblr = "N/A"
            else:
                kills = kd = finals = fkdr = wins = beds = wlr = bblr = "N/A"
        else:
            kills = kd = finals = fkdr = wins = beds = wlr = bblr = "N/A"

        # Map subcategories to values
        command_suffix_map = {
            'kills': kills,
            'kd': kd,
            'finals': finals,
            'fkdr': fkdr,
            'wins': wins,
            'beds': beds,
            'wlr': wlr,
            'bblr': bblr
        }

        # Format the response based on subcategory
        if subcategory == 'all':
            return (f"[{level_number}✫] {username} ┃ {stat_abbreviations['kills']} {kills} ┃ "
                    f"{stat_abbreviations['kd']} {kd} ┃ {stat_abbreviations['finals']} {finals} ┃ "
                    f"{stat_abbreviations['fkdr']} {fkdr} ┃ {stat_abbreviations['wins']} {wins} ┃ "
                    f"{stat_abbreviations['beds']} {beds} ┃ {stat_abbreviations['wlr']} {wlr} ┃ "
                    f"{stat_abbreviations['bblr']} {bblr}")
        else:
            # Handle multiple subcategories (e.g., 'fkdrFinals')
            subcategories_list = re.findall(r'[a-z]+|[A-Z][a-z]*', subcategory)
            results = []
            for sc in subcategories_list:
                sc_lower = sc.lower()
                variable = command_suffix_map.get(sc_lower, "N/A")
                abbr = stat_abbreviations.get(sc_lower, sc.upper())
                results.append(f"{abbr} {variable}")
            
            return f"[{level_number}✫] {username} ┃ {' ┃ '.join(results)}"