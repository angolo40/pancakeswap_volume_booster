import asyncio
import json

from aiogram import Bot, Dispatcher
from aiogram.types import ParseMode
from aiogram.utils import executor
from loguru import logger
from web3 import Web3, HTTPProvider

from random import randrange

from trader import Trader

logger.add('app.log', format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

bot: Bot
dp: Dispatcher

web3: Web3
trader: Trader
TX_URL: str

accounts = []
channel_id: int

max_INTERVAL: str(int)
min_INTERVAL: str(int)

force_Sell: str

def load_config():
    logger.info('Loading config...')
    with open('config.json') as f:
        return json.load(f)


def load_accounts():
    """Load ethereum wallets private keys from keys.txt file for making swaps"""
    logger.info('Loading accounts...')
    with open('keys.txt') as f:
        for key in f:
            key = key.strip()
            address = web3.eth.account.from_key(key).address
            accounts.append((address, key))


async def boost_volume(account):
    address, key = account
    logger.info('Volume Booster Start for account: ' + str(address))
    while True:
        tokens_amount = trader.get_token_balance(address)

        local_INTERVAL = randrange(min_INTERVAL, max_INTERVAL)
        logger.info('ACCOUNT: ' + str(address) + ' ---> Waiting ' + str(local_INTERVAL) + " secs before doing next operation")
        await asyncio.sleep(local_INTERVAL)

        if tokens_amount > 0:
            result = trader.sell(address, key, tokens_amount)
            await bot.send_message(channel_id,
                                   f'Sold {result["amount"]} {trader.symbol} tokens for {result["bnb"]} BNB\n{TX_URL % result["tx"]}')

            local_INTERVAL = randrange(min_INTERVAL, max_INTERVAL)
            logger.info('ACCOUNT: ' + str(address) + ' ---> Waiting ' + str(local_INTERVAL) + " secs before doing next operation")
            await asyncio.sleep(local_INTERVAL)


        bnb = trader.get_bnb_balance(address)

        if bnb > 0 and trader.can_buy(bnb, wallet=address) and force_Sell == False:
            result = trader.buy(address, key, bnb)
            await bot.send_message(channel_id,
                                   f'Bought {result["amount"]} {trader.symbol} tokens with {result["bnb"]} BNB\n{TX_URL % result["tx"]}')

def init():
    global bot, dp, web3, trader, TX_URL, max_INTERVAL, channel_id, min_INTERVAL, force_Sell
    config = load_config()
    web3 = Web3(HTTPProvider(config['bscNode']))
    TX_URL = config['txUrl']
    channel_id = config['channelId']
    max_INTERVAL = config['max_intervalInSeconds']
    min_INTERVAL = config['min_intervalInSeconds']
    force_Sell = config['force_Sell']

    router_abi = json.loads(config['pancakeswapRouterABI'])
    router_address = Web3.toChecksumAddress(config['pancakeSwapRouterAddress'])

    logger.info(f'Connected: {web3.isConnected()}')
    logger.info(f'Chain ID: {web3.eth.chainId}')

    token_address = Web3.toChecksumAddress(config['tokenAddress'])
    token_abi = json.loads(config['tokenABI'])
    token_contract = web3.eth.contract(address=token_address, abi=token_abi)

    bot = Bot(token=config['telegramBotToken'], parse_mode=ParseMode.HTML)
    dp = Dispatcher(bot)
    load_accounts()
    trader = Trader(web3, router_address, router_abi, token_contract, token_address)


async def on_bot_start_up(dispatcher) -> None:
    """List of actions which should be done before bot start"""
    logger.info('Start up')

    for account in accounts:
        asyncio.create_task(boost_volume(account))


if __name__ == '__main__':
    init()
    executor.start_polling(dp, skip_updates=True, on_startup=on_bot_start_up)
