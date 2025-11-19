from web3 import Web3
from eth_account import Account
from aiohttp import ClientSession, ClientTimeout, BasicAuth, TCPConnector
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import init, Fore, Style
import asyncio, random, time, os, pytz, re, sys

init(autoreset=True)
wib = pytz.timezone('Asia/Jakarta')

class Faroswap:
    def __init__(self):
        self.RPC_URL = "https://atlantic.dplabs-internal.com/"
        self.EXPLORER = "https://atlantic.pharosscan.xyz/tx/0x"
        self.PHRS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
        self.USDT = "0xE7E84B8B4f39C507499c40B4ac199B050e2882d5"
        self.USDC = "0xE0BE08c77f415F577A1B3A9aD7a1Df1479564ec8"
        self.DODO_APPROVE = "0x4Cf317b8918FbE8A890c01eDAb7d548555Ac2cE9"
        self.DODO_ROUTER = "0x819829e5CF6e19F9fED92F6b4CC1edF45a2cC4A2"
        self.POSITION_MANAGER = "0x1c430d84DD6185b1Ea2d4693e0033799d193542f"

        
        self.ABI = [
            {"inputs": [{"internalType": "address", "name": "owner", "type": "address"}, {"internalType": "address", "name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"internalType": "address", "name": "spender", "type": "address"}, {"internalType": "uint256", "name": "value", "type": "uint256"}], "name": "approve", "outputs": [{"internalType": "bool", "name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
            {"inputs": [{"internalType": "address", "name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
            {"inputs": [], "name": "decimals", "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
            {"inputs": [{"components": [
                {"internalType": "address", "name": "token0", "type": "address"},
                {"internalType": "address", "name": "token1", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
                {"internalType": "int24", "name": "tickLower", "type": "int24"},
                {"internalType": "int24", "name": "tickUpper", "type": "int24"},
                {"internalType": "uint256", "name": "amount0Desired", "type": "uint256"},
                {"internalType": "uint256", "name": "amount1Desired", "type": "uint256"},
                {"internalType": "uint256", "name": "amount0Min", "type": "uint256"},
                {"internalType": "uint256", "name": "amount1Min", "type": "uint256"},
                {"internalType": "address", "name": "recipient", "type": "address"},
                {"internalType": "uint256", "name": "deadline", "type": "uint256"}
            ], "internalType": "struct INonfungiblePositionManager.MintParams", "name": "params", "type": "tuple"}], "name": "mint", "outputs": [
                {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
                {"internalType": "uint128", "name": "liquidity", "type": "uint128"},
                {"internalType": "uint256", "name": "amount0", "type": "uint256"},
                {"internalType": "uint256", "name": "amount1", "type": "uint256"}
            ], "stateMutability": "payable", "type": "function"}
        ]

        self.proxies = []
        self.account_proxies = {}
        self.proxy_index = 0
        self.swap_count = self.phrs_amt = 0
        self.liq_count = self.liq_amt = 0
        self.min_delay = self.max_delay = 0
        self.option = 0
        self.use_proxy = False

    def log(self, msg):
        print(f"{Fore.CYAN}[ {datetime.now().astimezone(wib).strftime('%m/%d/%y %H:%M:%S')} ]{Fore.WHITE} | {msg}{Style.RESET_ALL}", flush=True)

    async def safe_input(self, prompt):
        """Safe input with timeout handling"""
        try:
            return await asyncio.wait_for(asyncio.to_thread(input, prompt), timeout=60.0)
        except asyncio.TimeoutError:
            self.log(f"{Fore.RED}Input timeout. Using default values.{Style.RESET_ALL}")
            return ""

    async def load_proxies(self, use_proxy_choice: int):
        filename = "proxy.txt"
        try:
            if use_proxy_choice == 1:
                async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                    async with session.get("https://raw.githubusercontent.com/monosans/proxy-list/refs/heads/main/proxies/http.txt") as response:
                        response.raise_for_status()
                        content = await response.text()
                        with open(filename, 'w') as f:
                            f.write(content)
                        self.proxies = [line.strip() for line in content.splitlines() if line.strip()]
            else:
                if not os.path.exists(filename):
                    self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                    return
                with open(filename, 'r') as f:
                    self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]
            
            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
            self.use_proxy = True
        
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []
            self.use_proxy = False

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, account):
        if account not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[account] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[account]

    def rotate_proxy_for_account(self, account):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[account] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None

        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy)
            return connector, None, None

        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                return None, clean_url, auth
            else:
                return None, proxy, None

        return None, None, None

    async def get_web3(self):
        for _ in range(5):
            try:
                w3 = Web3(Web3.HTTPProvider(self.RPC_URL, request_kwargs={'timeout': 60}))
                if await asyncio.to_thread(w3.is_connected):
                    return w3
                await asyncio.sleep(2)
            except Exception as e:
                self.log(f"{Fore.RED}RPC Connection Failed: {e}{Style.RESET_ALL}")
                await asyncio.sleep(2)
        raise Exception("RPC Failed after 5 attempts")

    async def fresh_nonce(self, w3, addr):
        for _ in range(3):
            try:
                return await asyncio.to_thread(w3.eth.get_transaction_count, addr, "pending")
            except Exception as e:
                self.log(f"{Fore.RED}Get Nonce Failed: {e}{Style.RESET_ALL}")
                await asyncio.sleep(2)
        raise Exception("Failed to get nonce")

    async def check_balance(self, w3, addr, token, min_amount):
        """Check token balance"""
        try:
            if token == self.PHRS:
                balance = await asyncio.to_thread(w3.eth.get_balance, addr)
                return balance >= min_amount
            else:
                contract = w3.eth.contract(address=token, abi=self.ABI)
                balance = await asyncio.to_thread(contract.functions.balanceOf(addr).call)
                return balance >= min_amount
        except Exception as e:
            self.log(f"{Fore.RED}Balance Check Failed: {e}{Style.RESET_ALL}")
            return False

    async def approve(self, w3, pk, addr, token, spender, amount):
        if token == self.PHRS: 
            return True
            
        try:
            contract = w3.eth.contract(address=token, abi=self.ABI)
            allowance = await asyncio.to_thread(contract.functions.allowance(addr, spender).call)
            if allowance >= amount: 
                return True
            
            max_fee = w3.to_wei(random.uniform(3.0, 4.0), 'gwei')
            priority_fee = w3.to_wei(random.uniform(1.5, 2.5), 'gwei')
            
            if priority_fee >= max_fee:
                priority_fee = max_fee - w3.to_wei(0.1, 'gwei')
            
            tx = contract.functions.approve(spender, 2**256-1).build_transaction({
                'nonce': await self.fresh_nonce(w3, addr),
                'gas': 100000,
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'chainId': w3.eth.chain_id
            })
            
            signed = w3.eth.account.sign_transaction(tx, pk)
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, h, timeout=300)
            self.log(f"{Fore.GREEN}Approved {token[2:8]}...{Style.RESET_ALL}")
            return True
        except Exception as e:
            self.log(f"{Fore.RED}Approve Failed: {e}{Style.RESET_ALL}")
            return False

    async def swap_with_proxy_retry(self, w3, pk, addr, from_token, to_token, amount, max_retries=10):
        """Swap with proxy rotation on no route errors"""
        dec = 18 if from_token == self.PHRS else 6
        amt_wei = int(amount * 10**dec)
        
        # PHRS to stable ဆိုတော့ approve မလိုပါ
        if from_token != self.PHRS:
            if not await self.approve(w3, pk, addr, from_token, self.DODO_APPROVE, amt_wei):
                return False

        retry_count = 0
        used_proxies = set()

        while retry_count < max_retries:
            proxy_url = self.get_next_proxy_for_account(addr) if self.use_proxy else None
            
            # Skip if we've already tried this proxy
            if proxy_url and proxy_url in used_proxies:
                proxy_url = self.rotate_proxy_for_account(addr)
            
            if proxy_url:
                used_proxies.add(proxy_url)
                self.log(f"{Fore.BLUE}Using Proxy ({retry_count + 1}/{max_retries}): {proxy_url}{Style.RESET_ALL}")
            else:
                self.log(f"{Fore.YELLOW}Using Direct Connection ({retry_count + 1}/{max_retries}){Style.RESET_ALL}")

            connector, proxy, auth = self.build_proxy_config(proxy_url)

            url = "https://api.dodoex.io/route-service/v2/widget/getdodoroute"
            params = {
                "chainId": "688689","fromTokenAddress": from_token,"toTokenAddress": to_token,
                "fromAmount": amt_wei,"userAddr": addr,"slippage": "10","deadLine": int(time.time())+600,
                "source": "dodoV2AndMixWasm","estimateGas": "true","apikey": "a37546505892e1a952"
            }
            
            try:
                async with ClientSession(timeout=ClientTimeout(total=60), connector=connector) as s:
                    async with s.get(url, params=params, proxy=proxy, proxy_auth=auth) as r:
                        data = await r.json()
                        if data.get("status") != 200:
                            self.log(f"{Fore.RED}No Route - Retrying with new proxy...{Style.RESET_ALL}")
                            retry_count += 1
                            
                            # Rotate proxy for next attempt
                            if self.use_proxy and self.proxies:
                                new_proxy = self.rotate_proxy_for_account(addr)
                                self.log(f"{Fore.YELLOW}Rotated to new proxy: {new_proxy}{Style.RESET_ALL}")
                            
                            await asyncio.sleep(2)
                            continue
                        route = data["data"]
                        
                # If we get here, we have a valid route
                self.log(f"{Fore.GREEN}Route found! Proceeding with swap...{Style.RESET_ALL}")
                return await self.execute_swap(w3, pk, addr, route, from_token)
                        
            except asyncio.TimeoutError:
                self.log(f"{Fore.RED}API Request Timeout - Retrying...{Style.RESET_ALL}")
                retry_count += 1
                if self.use_proxy and self.proxies:
                    new_proxy = self.rotate_proxy_for_account(addr)
                    self.log(f"{Fore.YELLOW}Rotated to new proxy after timeout: {new_proxy}{Style.RESET_ALL}")
                await asyncio.sleep(2)
                continue
            except Exception as e:
                self.log(f"{Fore.RED}API Request Failed: {e}{Style.RESET_ALL}")
                retry_count += 1
                
                if self.use_proxy and self.proxies:
                    new_proxy = self.rotate_proxy_for_account(addr)
                    self.log(f"{Fore.YELLOW}Rotated to new proxy after error: {new_proxy}{Style.RESET_ALL}")
                
                await asyncio.sleep(2)
                continue

        self.log(f"{Fore.RED}All {max_retries} swap attempts failed{Style.RESET_ALL}")
        return False

    async def execute_swap(self, w3, pk, addr, route, from_token):
        """Execute the swap transaction"""
        max_fee = w3.to_wei(random.uniform(3.0, 4.5), 'gwei')
        priority_fee = w3.to_wei(random.uniform(1.5, 2.8), 'gwei')
        
        if priority_fee >= max_fee:
            priority_fee = max_fee - w3.to_wei(0.1, 'gwei')

        tx = {
            'to': self.DODO_ROUTER,
            'data': route["data"],
            'value': int(route["value"]),
            'gas': int(route["gasLimit"]) + 200000,
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': priority_fee,
            'nonce': await self.fresh_nonce(w3, addr),
            'chainId': w3.eth.chain_id
        }

        for attempt in range(5):  # Reduce attempts to 5
            try:
                signed = w3.eth.account.sign_transaction(tx, pk)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                self.log(f"{Fore.YELLOW}Swap TX Sent → {tx_hash.hex()}{Style.RESET_ALL}")
                receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=300)
                explorer = f"{self.EXPLORER}{tx_hash.hex()}"
                if receipt.status == 1:
                    self.log(f"{Fore.GREEN}Swap Success!{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}TX Hash   → {tx_hash.hex()}{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}\n")
                    return True
                else:
                    self.log(f"{Fore.RED}Swap Reverted{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}\n")
                    return False
            except Exception as e:
                error_str = str(e)
                if any(k in error_str for k in ["113", "replay", "nonce"]):
                    tx['nonce'] = await self.fresh_nonce(w3, addr)
                    tx['maxFeePerGas'] = tx['maxFeePerGas'] + w3.to_wei(0.5, 'gwei')
                    tx['maxPriorityFeePerGas'] = min(tx['maxPriorityFeePerGas'] + w3.to_wei(0.3, 'gwei'), 
                                                   tx['maxFeePerGas'] - w3.to_wei(0.1, 'gwei'))
                    await asyncio.sleep(3)
                elif "PRIORITY_FEE_ABOVE_MAX_FEE" in error_str:
                    tx['maxPriorityFeePerGas'] = tx['maxFeePerGas'] - w3.to_wei(0.2, 'gwei')
                    await asyncio.sleep(2)
                elif "insufficient funds" in error_str.lower():
                    self.log(f"{Fore.RED}Insufficient funds for gas{Style.RESET_ALL}")
                    return False
                else:
                    self.log(f"{Fore.RED}Swap Error (Attempt {attempt + 1}/5): {e}{Style.RESET_ALL}")
                    if attempt < 4:
                        await asyncio.sleep(3)
                    else:
                        break
        return False

    async def swap(self, pk, addr, from_token, to_token, amount):
        try:
            w3 = await self.get_web3()
            return await self.swap_with_proxy_retry(w3, pk, addr, from_token, to_token, amount)
        except Exception as e:
            self.log(f"{Fore.RED}Swap Failed: {e}{Style.RESET_ALL}")
            return False

    async def add_liquidity(self, pk, addr):
        try:
            w3 = await self.get_web3()
            amt = int(self.liq_amt * 1e6)
            min_amt = int(amt * 0.98)  
            
            # Check balances
            usdc_balance_ok = await self.check_balance(w3, addr, self.USDC, amt)
            usdt_balance_ok = await self.check_balance(w3, addr, self.USDT, amt)
            
            if not usdc_balance_ok:
                self.log(f"{Fore.RED}Insufficient USDC balance. Need: {self.liq_amt}, Have: less{Style.RESET_ALL}")
                return False
            if not usdt_balance_ok:
                self.log(f"{Fore.RED}Insufficient USDT balance. Need: {self.liq_amt}, Have: less{Style.RESET_ALL}")
                return False

            self.log(f"{Fore.GREEN}Balance check passed. Proceeding with liquidity...{Style.RESET_ALL}")

            if not await self.approve(w3, pk, addr, self.USDC, self.POSITION_MANAGER, amt):
                return False
            if not await self.approve(w3, pk, addr, self.USDT, self.POSITION_MANAGER, amt):
                return False

            max_fee = w3.to_wei(random.uniform(3.5, 5.0), 'gwei')
            priority_fee = w3.to_wei(random.uniform(2.0, 3.5), 'gwei')
            
            if priority_fee >= max_fee:
                priority_fee = max_fee - w3.to_wei(0.1, 'gwei')

            contract = w3.eth.contract(self.POSITION_MANAGER, abi=self.ABI)
            params = (self.USDC, self.USDT, 500, -887270, 887270, amt, amt, min_amt, min_amt, addr, int(time.time())+600)
            
            tx = contract.functions.mint(params).build_transaction({
                'gas': 2000000,  
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': await self.fresh_nonce(w3, addr),
                'chainId': w3.eth.chain_id
            })

            for attempt in range(3):  # Reduce attempts to 3
                try:
                    signed = w3.eth.account.sign_transaction(tx, pk)
                    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                    self.log(f"{Fore.YELLOW}Liquidity TX Sent → {tx_hash.hex()}{Style.RESET_ALL}")
                    receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=300)
                    explorer = f"{self.EXPLORER}{tx_hash.hex()}"
                    if receipt.status == 1:
                        self.log(f"{Fore.GREEN}Liquidity Added!{Style.RESET_ALL}")
                        self.log(f"{Fore.CYAN}TX Hash   → {tx_hash.hex()}{Style.RESET_ALL}")
                        self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}\n")
                        return True
                    else:
                        self.log(f"{Fore.RED}Liquidity Reverted{Style.RESET_ALL}")
                        self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}")
                        return False
                except Exception as e:
                    error_str = str(e)
                    if any(k in error_str for k in ["113", "replay", "nonce"]):
                        tx['nonce'] = await self.fresh_nonce(w3, addr)
                        await asyncio.sleep(3)
                    elif "insufficient funds" in error_str.lower():
                        self.log(f"{Fore.RED}Insufficient funds for gas + value{Style.RESET_ALL}")
                        return False
                    else:
                        self.log(f"{Fore.RED}Liquidity Error (Attempt {attempt + 1}/3): {e}{Style.RESET_ALL}")
                        if attempt < 2:
                            await asyncio.sleep(3)
                        else:
                            break
            return False
        except Exception as e:
            self.log(f"{Fore.RED}Liquidity Failed: {e}{Style.RESET_ALL}")
            return False

    async def delay(self):
        d = random.randint(self.min_delay, self.max_delay)
        for i in range(d, 0, -1):
            print(f"{Fore.BLUE}Waiting {i}s...{Style.RESET_ALL}", end="\r", flush=True)
            await asyncio.sleep(1)
        print(" " * 60, end="\r")

    async def menu(self):
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"{Fore.GREEN + Style.BRIGHT}   FAROSWAP ATLANTIC AUTO BOT {Style.RESET_ALL}\n")
            print(f"{Fore.YELLOW}PHRS to STABLE ONLY SWAP{Style.RESET_ALL}")
            
            print(f"{Fore.YELLOW}Proxy Options:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}0. No Proxy (Direct Connection){Style.RESET_ALL}")
            print(f"{Fore.CYAN}1. Download Fresh Proxies{Style.RESET_ALL}")
            print(f"{Fore.CYAN}2. Use Local proxy.txt{Style.RESET_ALL}")
            
            proxy_input = await self.safe_input(f"{Fore.YELLOW}Choose Proxy Option [0-2]: {Style.RESET_ALL}")
            proxy_choice = int(proxy_input) if proxy_input.strip() else 0
            
            if proxy_choice in [1, 2]:
                await self.load_proxies(proxy_choice)
            else:
                self.log(f"{Fore.YELLOW}Using Direct Connection (No Proxy){Style.RESET_ALL}")

            print(f"\n{Fore.YELLOW}1. PHRS to Stable Swap    2. Add Liquidity    3. Run All{Style.RESET_ALL}")
            option_input = await self.safe_input(f"{Fore.CYAN}Choose [1-3]: {Style.RESET_ALL}")
            self.option = int(option_input) if option_input.strip() else 1

            if self.option in [1, 3]:
                swap_count_input = await self.safe_input(f"{Fore.YELLOW}Swap Count       → {Style.RESET_ALL}")
                self.swap_count = int(swap_count_input) if swap_count_input.strip() else 1
                
                phrs_amt_input = await self.safe_input(f"PHRS Amount      → {Style.RESET_ALL}")
                self.phrs_amt = float(phrs_amt_input) if phrs_amt_input.strip() else 0.001

            if self.option in [2, 3]:
                liq_count_input = await self.safe_input(f"{Fore.YELLOW}Liquidity Count  → {Style.RESET_ALL}")
                self.liq_count = int(liq_count_input) if liq_count_input.strip() else 1
                
                liq_amt_input = await self.safe_input(f"USDC/USDT Amount → {Style.RESET_ALL}")
                self.liq_amt = float(liq_amt_input) if liq_amt_input.strip() else 0.01

            min_delay_input = await self.safe_input(f"{Fore.YELLOW}Min Delay (s)    → {Style.RESET_ALL}")
            self.min_delay = int(float(min_delay_input)) if min_delay_input.strip() else 5
            
            max_delay_input = await self.safe_input(f"{Fore.YELLOW}Max Delay (s)    → {Style.RESET_ALL}")
            self.max_delay = int(float(max_delay_input)) if max_delay_input.strip() else 15
            
            if self.min_delay > self.max_delay:
                self.min_delay, self.max_delay = self.max_delay, self.min_delay
                
        except Exception as e:
            self.log(f"{Fore.RED}Menu Error: {e}{Style.RESET_ALL}")
            # Set default values
            self.option = 1
            self.swap_count = 1
            self.phrs_amt = 0.001
            self.min_delay = 5
            self.max_delay = 15

    async def run(self):
        try:
            await self.menu()
            
            if not os.path.exists("accounts.txt"):
                self.log(f"{Fore.RED}accounts.txt file not found!{Style.RESET_ALL}")
                return
                
            with open("accounts.txt") as f:
                pks = [l.strip() for l in f if l.strip()]
                
            if not pks:
                self.log(f"{Fore.RED}No private keys found in accounts.txt!{Style.RESET_ALL}")
                return

            self.log(f"{Fore.GREEN}Starting with {len(pks)} accounts...{Style.RESET_ALL}")

            while True:
                for pk in pks:
                    try:
                        addr = Account.from_key(pk).address
                        self.log(f"{Fore.MAGENTA}═{'═'*20} {addr[:10]}...{addr[-8:]} {'═'*20}{Style.RESET_ALL}")

                        # PHRS to stable pairs only
                        pairs = [
                            (self.PHRS, self.USDT, self.phrs_amt),
                            (self.PHRS, self.USDC, self.phrs_amt),
                        ]

                        if self.option in [1, 3]:
                            for i in range(self.swap_count):
                                f, t, a = random.choice(pairs)
                                to_token_name = "USDT" if t == self.USDT else "USDC"
                                self.log(f"{Fore.WHITE}Swap {i+1}/{self.swap_count} | {a} PHRS → {to_token_name}")
                                await self.swap(pk, addr, f, t, a)
                                await self.delay()

                        if self.option in [2, 3]:
                            for i in range(self.liq_count):
                                self.log(f"{Fore.WHITE}Liquidity {i+1}/{self.liq_count} | {self.liq_amt} USDC+USDT")
                                await self.add_liquidity(pk, addr)
                                await self.delay()

                    except Exception as e:
                        self.log(f"{Fore.RED}Account processing failed: {e}{Style.RESET_ALL}")
                        continue

                self.log(f"{Fore.CYAN}Round Done! Restarting in 2min...{Style.RESET_ALL}")
                await asyncio.sleep(120)  # Reduce to 2 minutes
                
        except KeyboardInterrupt:
            self.log(f"{Fore.YELLOW}Bot stopped by user{Style.RESET_ALL}")
        except Exception as e:
            self.log(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
            self.log(f"{Fore.YELLOW}Restarting in 10 seconds...{Style.RESET_ALL}")
            await asyncio.sleep(10)
            await self.run()  # Restart

if __name__ == "__main__":
    try:
        asyncio.run(Faroswap().run())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Bot stopped{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Fatal error: {e}{Style.RESET_ALL}")
