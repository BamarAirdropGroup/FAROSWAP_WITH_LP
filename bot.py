from web3 import Web3
from eth_account import Account
from aiohttp import ClientSession, ClientTimeout, BasicAuth, TCPConnector
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from datetime import datetime
from colorama import init, Fore, Style
import asyncio, random, time, os, pytz, re

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
        self.swap_count = self.phrs_amt = self.usdt_amt = self.usdc_amt = 0
        self.liq_count = self.liq_amt = 0
        self.min_delay = self.max_delay = 0
        self.option = 0
        self.use_proxy = False

    def log(self, msg):
        print(f"{Fore.CYAN}[ {datetime.now().astimezone(wib).strftime('%m/%d/%y %H:%M:%S')} ]{Fore.WHITE} | {msg}{Style.RESET_ALL}", flush=True)

   
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

        raise Exception("Unsupported Proxy Type.")

    async def get_web3(self):
        w3 = Web3(Web3.HTTPProvider(self.RPC_URL))
        for _ in range(5):
            try:
                await asyncio.to_thread(w3.eth.get_block_number)
                return w3
            except:
                await asyncio.sleep(2)
        raise Exception("RPC Failed")

    async def fresh_nonce(self, w3, addr):
        return await asyncio.to_thread(w3.eth.get_transaction_count, addr, "pending")

    async def check_balance(self, w3, addr, token, min_amount):
        """Check token balance"""
        if token == self.PHRS:
            balance = await asyncio.to_thread(w3.eth.get_balance, addr)
            return balance >= min_amount
        else:
            contract = w3.eth.contract(address=token, abi=self.ABI)
            balance = await asyncio.to_thread(contract.functions.balanceOf(addr).call)
            return balance >= min_amount

    async def approve(self, w3, pk, addr, token, spender, amount):
        if token == self.PHRS: return True
        contract = w3.eth.contract(address=token, abi=self.ABI)
        allowance = await asyncio.to_thread(contract.functions.allowance(addr, spender).call)
        if allowance >= amount: return True
        
        
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

    async def swap(self, pk, addr, from_token, to_token, amount):
        w3 = await self.get_web3()
        dec = 18 if from_token == self.PHRS else 6
        amt_wei = int(amount * 10**dec)
        await self.approve(w3, pk, addr, from_token, self.DODO_APPROVE, amt_wei)

        
        proxy_url = self.get_next_proxy_for_account(addr) if self.use_proxy else None
        connector, proxy, auth = self.build_proxy_config(proxy_url)
        
        if proxy_url:
            self.log(f"{Fore.BLUE}Using Proxy: {proxy_url}{Style.RESET_ALL}")
        else:
            self.log(f"{Fore.YELLOW}Using Direct Connection{Style.RESET_ALL}")

        url = "https://api.dodoex.io/route-service/v2/widget/getdodoroute"
        params = {
            "chainId": "688689","fromTokenAddress": from_token,"toTokenAddress": to_token,
            "fromAmount": amt_wei,"userAddr": addr,"slippage": "10","deadLine": int(time.time())+600,
            "source": "dodoV2AndMixWasm","estimateGas": "true","apikey": "a37546505892e1a952"
        }
        
        try:
            async with ClientSession(timeout=ClientTimeout(60), connector=connector) as s:
                async with s.get(url, params=params, proxy=proxy, proxy_auth=auth) as r:
                    data = await r.json()
                    if data.get("status") != 200:
                        self.log(f"{Fore.RED}No Route{Style.RESET_ALL}")
                        # Rotate proxy on failure
                        if self.use_proxy:
                            new_proxy = self.rotate_proxy_for_account(addr)
                            self.log(f"{Fore.YELLOW}Rotated to new proxy: {new_proxy}{Style.RESET_ALL}")
                        return
                    route = data["data"]
        except Exception as e:
            self.log(f"{Fore.RED}API Request Failed: {e}{Style.RESET_ALL}")
            
            if self.use_proxy:
                new_proxy = self.rotate_proxy_for_account(addr)
                self.log(f"{Fore.YELLOW}Rotated to new proxy after error: {new_proxy}{Style.RESET_ALL}")
            return

        
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

        for attempt in range(10):
            try:
                signed = w3.eth.account.sign_transaction(tx, pk)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                self.log(f"{Fore.YELLOW}Swap TX Sent → {tx_hash.hex()}{Style.RESET_ALL}")
                receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=500)
                explorer = f"{self.EXPLORER}{tx_hash.hex()}"
                if receipt.status == 1:
                    self.log(f"{Fore.GREEN}Swap Success!{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}TX Hash   → {tx_hash.hex()}{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}\n")
                else:
                    self.log(f"{Fore.RED}Swap Reverted{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}\n")
                return
            except Exception as e:
                if any(k in str(e) for k in ["113", "replay", "nonce"]):
                    tx['nonce'] = await self.fresh_nonce(w3, addr)
                    
                    tx['maxFeePerGas'] = tx['maxFeePerGas'] + w3.to_wei(0.5, 'gwei')
                    tx['maxPriorityFeePerGas'] = min(tx['maxPriorityFeePerGas'] + w3.to_wei(0.3, 'gwei'), 
                                                   tx['maxFeePerGas'] - w3.to_wei(0.1, 'gwei'))
                    await asyncio.sleep(5)
                elif "PRIORITY_FEE_ABOVE_MAX_FEE" in str(e):
                    
                    self.log(f"{Fore.RED}Fee adjustment needed, retrying...{Style.RESET_ALL}")
                    tx['maxPriorityFeePerGas'] = tx['maxFeePerGas'] - w3.to_wei(0.2, 'gwei')
                    await asyncio.sleep(3)
                else:
                    self.log(f"{Fore.RED}Swap Error (Attempt {attempt + 1}/10): {e}{Style.RESET_ALL}")
                    if attempt < 9:
                        await asyncio.sleep(5)
                    else:
                        break

    async def add_liquidity(self, pk, addr):
        w3 = await self.get_web3()
        amt = int(self.liq_amt * 1e6)
        min_amt = int(amt * 0.98)  
        
        
        usdc_balance_ok = await self.check_balance(w3, addr, self.USDC, amt)
        usdt_balance_ok = await self.check_balance(w3, addr, self.USDT, amt)
        
        if not usdc_balance_ok:
            self.log(f"{Fore.RED}Insufficient USDC balance. Need: {self.liq_amt}, Have: less{Style.RESET_ALL}")
            return
        if not usdt_balance_ok:
            self.log(f"{Fore.RED}Insufficient USDT balance. Need: {self.liq_amt}, Have: less{Style.RESET_ALL}")
            return

        self.log(f"{Fore.GREEN}Balance check passed. Proceeding with liquidity...{Style.RESET_ALL}")

        await self.approve(w3, pk, addr, self.USDC, self.POSITION_MANAGER, amt)
        await self.approve(w3, pk, addr, self.USDT, self.POSITION_MANAGER, amt)

        
        max_fee = w3.to_wei(random.uniform(3.5, 5.0), 'gwei')
        priority_fee = w3.to_wei(random.uniform(2.0, 3.5), 'gwei')
        
        
        if priority_fee >= max_fee:
            priority_fee = max_fee - w3.to_wei(0.1, 'gwei')

        contract = w3.eth.contract(self.POSITION_MANAGER, abi=self.ABI)
        params = (self.USDC, self.USDT, 500, -887270, 887270, amt, amt, min_amt, min_amt, addr, int(time.time())+600)
        
        try:
            tx = contract.functions.mint(params).build_transaction({
                'gas': 2000000,  
                'maxFeePerGas': max_fee,
                'maxPriorityFeePerGas': priority_fee,
                'nonce': await self.fresh_nonce(w3, addr),
                'chainId': w3.eth.chain_id
            })
        except Exception as e:
            self.log(f"{Fore.RED}Failed to build transaction: {e}{Style.RESET_ALL}")
            return

        for attempt in range(5):
            try:
                signed = w3.eth.account.sign_transaction(tx, pk)
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                self.log(f"{Fore.YELLOW}Liquidity TX Sent → {tx_hash.hex()}{Style.RESET_ALL}")
                receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash, timeout=500)
                explorer = f"{self.EXPLORER}{tx_hash.hex()}"
                if receipt.status == 1:
                    self.log(f"{Fore.GREEN}Liquidity Added!{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}TX Hash   → {tx_hash.hex()}{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}\n")
                    
                    
                    if receipt.logs:
                        self.log(f"{Fore.GREEN}Position created with {len(receipt.logs)} events{Style.RESET_ALL}")
                    else:
                        self.log(f"{Fore.YELLOW}No position events detected (might be dust amount){Style.RESET_ALL}")
                else:
                    self.log(f"{Fore.RED}Liquidity Reverted{Style.RESET_ALL}")
                    self.log(f"{Fore.CYAN}Explorer  → {explorer}{Style.RESET_ALL}")
                    
                    
                    try:
                        
                        self.log(f"{Fore.YELLOW}Analyzing revert reason...{Style.RESET_ALL}")
                        await asyncio.to_thread(w3.eth.call, tx, receipt.blockNumber - 1)
                    except Exception as sim_error:
                        self.log(f"{Fore.RED}Revert reason: {sim_error}{Style.RESET_ALL}")
                return
            except Exception as e:
                if "113" in str(e) or "replay" in str(e).lower() or "nonce" in str(e).lower():
                    tx['nonce'] = await self.fresh_nonce(w3, addr)
                    await asyncio.sleep(6)
                elif "PRIORITY_FEE_ABOVE_MAX_FEE" in str(e):
                    
                    self.log(f"{Fore.RED}Fee adjustment needed for liquidity, retrying...{Style.RESET_ALL}")
                    tx['maxPriorityFeePerGas'] = tx['maxFeePerGas'] - w3.to_wei(0.2, 'gwei')
                    await asyncio.sleep(3)
                elif "insufficient funds" in str(e).lower():
                    self.log(f"{Fore.RED}Insufficient funds for gas + value{Style.RESET_ALL}")
                    return
                else:
                    self.log(f"{Fore.RED}Liquidity Error (Attempt {attempt + 1}/5): {e}{Style.RESET_ALL}")
                    if attempt < 4:
                        await asyncio.sleep(5)
                    else:
                        self.log(f"{Fore.RED}All liquidity attempts failed{Style.RESET_ALL}")
                        break

    async def delay(self):
        d = random.randint(self.min_delay, self.max_delay)
        for i in range(d, 0, -1):
            print(f"{Fore.BLUE}Waiting {i}s...{Style.RESET_ALL}", end="\r", flush=True)
            await asyncio.sleep(1)
        print(" " * 60, end="\r")

    async def menu(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.GREEN + Style.BRIGHT}   FAROSWAP ATLANTIC AUTO BOT {Style.RESET_ALL}\n")
        
        
        print(f"{Fore.YELLOW}Proxy Options:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}0. No Proxy (Direct Connection){Style.RESET_ALL}")
        print(f"{Fore.CYAN}1. Download Fresh Proxies{Style.RESET_ALL}")
        print(f"{Fore.CYAN}2. Use Local proxy.txt{Style.RESET_ALL}")
        proxy_choice = int(input(f"{Fore.YELLOW}Choose Proxy Option [0-2]: {Style.RESET_ALL}"))
        
        if proxy_choice in [1, 2]:
            await self.load_proxies(proxy_choice)
        else:
            self.log(f"{Fore.YELLOW}Using Direct Connection (No Proxy){Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}1. Random Swap    2. Add Liquidity    3. Run All{Style.RESET_ALL}")
        self.option = int(input(f"{Fore.CYAN}Choose [1-3]: {Style.RESET_ALL}"))

        if self.option in [1, 3]:
            self.swap_count = int(input(f"{Fore.YELLOW}Swap Count       → {Style.RESET_ALL}"))
            self.phrs_amt   = float(input(f"PHRS Amount      → {Style.RESET_ALL}"))
            self.usdt_amt   = float(input(f"USDT Amount      → {Style.RESET_ALL}"))
            self.usdc_amt   = float(input(f"USDC Amount      → {Style.RESET_ALL}"))

        if self.option in [2, 3]:
            self.liq_count = int(input(f"{Fore.YELLOW}Liquidity Count  → {Style.RESET_ALL}"))
            self.liq_amt   = float(input(f"USDC/USDT Amount → {Style.RESET_ALL}"))
            
            
            if self.liq_amt < 0.01:
                self.log(f"{Fore.YELLOW}Warning: Amount {self.liq_amt} might be too small. Recommended: 0.01+{Style.RESET_ALL}")
                confirm = input(f"{Fore.YELLOW}Continue with small amount? (y/n): {Style.RESET_ALL}")
                if confirm.lower() != 'y':
                    self.liq_amt = float(input(f"Enter new USDC/USDT Amount → {Style.RESET_ALL}"))

        try:
            self.min_delay = int(float(input(f"{Fore.YELLOW}Min Delay (s)    → {Style.RESET_ALL}")))
        except:
            self.min_delay = 5
        try:
            self.max_delay = int(float(input(f"{Fore.YELLOW}Max Delay (s)    → {Style.RESET_ALL}")))
        except:
            self.max_delay = 15
        if self.min_delay > self.max_delay:
            self.min_delay, self.max_delay = self.max_delay, self.min_delay

    async def run(self):
        await self.menu()
        with open("accounts.txt") as f:
            pks = [l.strip() for l in f if l.strip()]

        while True:
            for pk in pks:
                addr = Account.from_key(pk).address
                self.log(f"{Fore.MAGENTA}═{'═'*20} {addr[:10]}...{addr[-8:]} {'═'*20}{Style.RESET_ALL}")

                pairs = [
                    (self.PHRS, self.USDT, self.phrs_amt),
                    (self.PHRS, self.USDC, self.phrs_amt),
                    (self.USDT, self.PHRS, self.usdt_amt),
                    (self.USDC, self.PHRS, self.usdc_amt),
                ]

                if self.option in [1, 3]:
                    for i in range(self.swap_count):
                        f, t, a = random.choice(pairs)
                        from_n = "PHRS" if f == self.PHRS else "STABLE"
                        to_n   = "PHRS" if t == self.PHRS else "STABLE"
                        self.log(f"{Fore.WHITE}Swap {i+1}/{self.swap_count} | {a} {from_n} → {to_n}")
                        await self.swap(pk, addr, f, t, a)
                        await self.delay()

                if self.option in [2, 3]:
                    for i in range(self.liq_count):
                        self.log(f"{Fore.WHITE}Liquidity {i+1}/{self.liq_count} | {self.liq_amt} USDC+USDT")
                        await self.add_liquidity(pk, addr)
                        await self.delay()

            self.log(f"{Fore.CYAN}Round Done! Restarting in 5min...{Style.RESET_ALL}")
            await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(Faroswap().run())
