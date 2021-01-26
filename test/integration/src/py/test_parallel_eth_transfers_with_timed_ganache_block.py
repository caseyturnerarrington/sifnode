import concurrent
import logging
import math
import multiprocessing
import os
from concurrent.futures.thread import ThreadPoolExecutor

import burn_lock_functions
import test_utilities
from burn_lock_functions import EthereumToSifchainTransferRequest
from integration_env_credentials import sifchain_cli_credentials_for_test
from test_utilities import get_required_env_var, get_shell_output, get_optional_env_var, ganache_owner_account

smart_contracts_dir = get_required_env_var("SMART_CONTRACTS_DIR")

ethereum_address = get_optional_env_var(
    "ETHEREUM_ADDRESS",
    ganache_owner_account(smart_contracts_dir)
)
test_amount = 20000


def test_transfer_eth_to_ceth_in_parallel():
    test_utilities.set_lock_burn_limit(smart_contracts_dir, "eth", test_amount)
    logging.info("restart ganache with timed blocks")
    integration_dir = os.environ.get("TEST_INTEGRATION_DIR")
    get_shell_output(f"{integration_dir}/ganache_start.sh 5")
    n_parallel_tasks = multiprocessing.cpu_count() - 2
    with concurrent.futures.ThreadPoolExecutor(n_parallel_tasks) as executor:
        futures = {executor.submit(execute_one_transfer, x) for x in range(0, n_parallel_tasks)}
        for f in concurrent.futures.as_completed(futures):
            # As a side effect, this will raise any exception that happened in the future
            logging.info(f"Parallel result: {f.result()}")
    logging.info("restart ganache without timed blocks")
    get_shell_output(f"{integration_dir}/ganache_start.sh")


def execute_one_transfer(id_number: int):
    logging.info(f"starting request {id_number}")
    new_account_key = get_shell_output("uuidgen")
    credentials = sifchain_cli_credentials_for_test(new_account_key)
    new_addr = burn_lock_functions.create_new_sifaddr(credentials=credentials, keyname=new_account_key)
    credentials.from_key = new_addr["name"]
    request = EthereumToSifchainTransferRequest(
        sifchain_address=new_addr["address"],
        smart_contracts_dir=smart_contracts_dir,
        ethereum_address=ethereum_address,
        ethereum_private_key_env_var="ETHEREUM_PRIVATE_KEY",
        bridgebank_address=get_required_env_var("BRIDGE_BANK_ADDRESS"),
        ethereum_network=(os.environ.get("ETHEREUM_NETWORK") or ""),
        amount=test_amount,
        ceth_amount=2 * (10 ** 16),
        manual_block_advance=False,
    )
    logging.info(f"execute request #{id_number}")
    burn_lock_functions.transfer_ethereum_to_sifchain(request, 90)
    return f"transaction {id_number} transfered eth to ceth: {request}"
