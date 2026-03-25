import os
import time
import glob
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from logger_config import logger

class BaseSiteAutomation:
    def __init__(self, driver, empresa_config, download_dir):
        self.driver = driver
        self.config = empresa_config
        self.empresa = self.config.get('empresa', 'desconhecida').upper()
        self.download_dir = download_dir
        self.wait = WebDriverWait(self.driver, 20)
        self.short_wait = WebDriverWait(self.driver, 5)

    def wait_for_element(self, by, value, timeout=20):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.error(f"[{self.empresa}] Timeout esperando pelo elemento: {value}")
            raise

    def wait_for_clickable(self, by, value, timeout=20):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            logger.error(f"[{self.empresa}] Timeout esperando elemento ser clicável: {value}")
            raise

    def get_latest_downloaded_file(self):
        list_of_files = glob.glob(os.path.join(self.download_dir, '*'))
        if not list_of_files:
            return None
        valid_files = [f for f in list_of_files if not f.endswith('.crdownload')]
        if not valid_files:
            return None
        latest_file = max(valid_files, key=os.path.getctime)
        return latest_file

    def wait_for_download(self, timeout=60):
        logger.info(f"[{self.empresa}] Aguardando conclusão do download...")
        end_time = time.time() + timeout
        while time.time() < end_time:
            crdownloads = glob.glob(os.path.join(self.download_dir, '*.crdownload'))
            if not crdownloads:
                latest = self.get_latest_downloaded_file()
                if latest:
                    if os.path.getsize(latest) > 0:
                        logger.info(f"[{self.empresa}] Download concluído: {os.path.basename(latest)}")
                        return True
            time.sleep(1)
        logger.error(f"[{self.empresa}] Timeout aguardando finalização do download.")
        return False

class CPFLAutomation(BaseSiteAutomation):
    def executar(self):
        try:
            self._realizar_login()
            self._selecionar_perfil_empresas()
            self._navegar_e_acessar_instalacao()
            self._baixar_faturas_instalacao_principal()
            self._baixar_faturas_outras_instalacoes()
            return True
        except Exception as e:
            logger.error(f"[{self.empresa}] Falha na execução da automação: {str(e)}")
            return False

    def _realizar_login(self):
        logger.info(f"[{self.empresa}] Acessando página de login: {self.config.get('url_login')}")
        self.driver.get(self.config.get('url_login'))
        
        try:
            user_input = self.wait_for_clickable(By.ID, "signInName")
            user_input.clear()
            user_input.send_keys(self.config['usuario'])
            
            pass_input = self.wait_for_clickable(By.ID, "password")
            pass_input.clear()
            pass_input.send_keys(self.config['senha'])
            
            btn_login = self.wait_for_clickable(By.ID, "next")
            btn_login.click()
            
            logger.info(f"[{self.empresa}] Login enviado. Aguardando processamento...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[{self.empresa}] Falha de login: {e}")
            raise

    def _selecionar_perfil_empresas(self):
        logger.info(f"[{self.empresa}] Selecionando perfil 'CPFL Empresas'...")
        try:
            # Using XPath to find the button by text as it's more stable across refreshes
            xpath_empresas = "//*[contains(text(), 'CPFL Empresas')]"
            btn_empresas = self.wait_for_clickable(By.XPATH, xpath_empresas)
            btn_empresas.click()
            time.sleep(3)
        except Exception as e:
            logger.warning(f"[{self.empresa}] Botão 'CPFL Empresas' não encontrado ou já passou: {e}")

    def _navegar_e_acessar_instalacao(self):
        try:
            logger.info(f"[{self.empresa}] Clicando em 'Débitos e 2ª via'...")
            xpath_debitos = "//*[contains(text(), 'Débitos e 2ª via')]"
            self.wait_for_clickable(By.XPATH, xpath_debitos).click()
            
            logger.info(f"[{self.empresa}] Clicando em 'Conta Completa'...")
            xpath_completa = "//*[contains(text(), 'Conta Completa')]"
            self.wait_for_clickable(By.XPATH, xpath_completa).click()
            
            time.sleep(5)
            logger.info(f"[{self.empresa}] Selecionando primeira instalação...")
            # Assuming the first checkbox in the list
            checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
            if checkboxes:
                checkboxes[0].click()
            
            logger.info(f"[{self.empresa}] Clicando em 'Acessar'...")
            btn_acessar = self.wait_for_clickable(By.XPATH, "//*[contains(text(), 'Acessar')]")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn_acessar)
            btn_acessar.click()
            
            time.sleep(5)
        except Exception as e:
            logger.error(f"[{self.empresa}] Erro ao navegar e acessar instalação: {e}")
            raise

    def _baixar_faturas_instalacao_principal(self):
        try:
            logger.info(f"[{self.empresa}] Clicando em 'Débitos e segunda via' novamente...")
            xpath_debitos = "//*[contains(text(), 'Débitos e segunda via')]"
            self.wait_for_clickable(By.XPATH, xpath_debitos).click()
            
            self._fechar_propaganda()
            
            logger.info(f"[{self.empresa}] Selecionando fatura e imprimindo...")
            self._processar_download_fatura()
        except Exception as e:
            logger.error(f"[{self.empresa}] Erro ao baixar fatura da instalação principal: {e}")
            raise

    def _baixar_faturas_outras_instalacoes(self):
        try:
            logger.info(f"[{self.empresa}] Buscando outras instalações...")

            xpath_outras = "//*[contains(text(), 'Ver Débitos de Outras Instalações')]"
            btn_outras = self.wait_for_clickable(By.XPATH, xpath_outras)

            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn_outras)
            self.driver.execute_script("arguments[0].click();", btn_outras)

            time.sleep(5)
            # Find all "+" buttons to expand installations
            # Using a more generic class or text search if "+" is text

            xpath_expand = "//button[contains(., '+')] | //span[contains(., '+')]"

            total = len(self.driver.find_elements(By.XPATH, xpath_expand))
            logger.info(f"[{self.empresa}] Encontradas {total} instalações.")

            for i in range(total):
                try:
                    expand_buttons = self.driver.find_elements(By.XPATH, xpath_expand)
                    btn = expand_buttons[i]

                    # scroll + click seguro
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    self.driver.execute_script("arguments[0].click();", btn)

                    
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='checkbox']"))
                    )

                    self._processar_download_fatura()

                except Exception as inner_e:
                    logger.warning(f"[{self.empresa}] Erro ao processar instalação {i}: {inner_e}")
                    continue

        except Exception as e:
            logger.error(f"[{self.empresa}] Erro ao processar outras instalações: {e}")

    def _fechar_propaganda(self):
        try:
            # Common patterns for close buttons in popups
            close_selectors = [
                (By.XPATH, "//*[@class='close']"),
                (By.XPATH, "//*[contains(@class, 'close')]"),
                (By.XPATH, "//*[text()='x' or text()='X']"),
                (By.CSS_SELECTOR, ".modal-header .close")
            ]
            for by, val in close_selectors:
                try:
                    btn = self.short_wait.until(EC.element_to_be_clickable((by, val)))
                    btn.click()
                    logger.info(f"[{self.empresa}] Propaganda fechada.")
                    return
                except:
                    continue
        except:
            pass

    def _processar_download_fatura(self):
        logger.info(f"[{self.empresa}] Selecionando checkbox da fatura...")
        checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        if checkboxes:
            # Click the first one that is likely the most recent
            self.driver.execute_script("arguments[0].click();", checkboxes[0])
            
            logger.info(f"[{self.empresa}] Clicando em 'Imprimir'...")
            # The "Imprimir" might be a link with an icon or text
            xpath_imprimir = "//*[contains(text(), 'Imprimir')]"
            self.wait_for_clickable(By.XPATH, xpath_imprimir).click()
            
            time.sleep(3)
            logger.info(f"[{self.empresa}] Clicando em 'Imprimir' na janela simplificada...")
            # Second imprimir in the modal/popover
            btn_imprimir_modal = self.wait_for_clickable(By.XPATH, "//button[contains(text(), 'Imprimir')]")
            btn_imprimir_modal.click()
            
            # Now handle the PDF save (usually opens in a new tab or triggers a print dialog)
            # This part is tricky with Selenium if it's a browser print dialog.
            # However, if it's a PDF stream, it might download automatically if Chrome is configured.
            logger.info(f"[{self.empresa}] Aguardando conclusão do download do PDF...")
            self.wait_for_download()

# Sabesp and DAE automations removed at user request.