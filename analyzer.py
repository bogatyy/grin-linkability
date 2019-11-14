from collections import defaultdict
import gzip
import requests

BLOCK_START = 164696
BLOCK_FINISH = 170350

PREFIX = 'WARN grin_servers::common::hooks - Received tx'


def parse_commitments(line):
    PREFIX = 'Commitment('
    SUFFIX = ')'
    SEPARATOR = ', '
    items = line.split(SEPARATOR)
    for item in items:
        assert item.startswith(PREFIX) and item.endswith(SUFFIX) and len(item) == 78
    return [item[len(PREFIX):-len(SUFFIX)] for item in items]


def parse_logged_transaction(line):
    if PREFIX not in line:
        return None
    line = line[line.index(', ') + 2:]
    counts = line[:line.index(' ')]
    n_inputs, n_outputs, n_kernels = (int(number) for number in counts.split('/'))
    assert 'Inputs' in line and 'Outputs' in line and 'Kernels' in line
    # parse inputs
    inputs_str = line[line.index('[') + 1:line.index(']')]
    inputs = parse_commitments(inputs_str)
    assert len(inputs) == n_inputs
    line = line[line.index(']') + 1:]
    # parse outputs
    outputs_str = line[line.index('[') + 1:line.index(']')]
    outputs = parse_commitments(outputs_str)
    assert len(outputs) == n_outputs
    line = line[line.index(']') + 1:]
    # parse kernels
    kernels_str = line[line.index('[') + 1:line.index(']')]
    kernels = parse_commitments(kernels_str)
    assert len(kernels) == n_kernels
    # tuple to make it hashable
    return (tuple(inputs), tuple(outputs), tuple(kernels))


def extract_transactions_from_log(filename):
    log_lines = gzip.open(filename, 'rt').readlines()
    transactions = [parse_logged_transaction(line) for line in log_lines if PREFIX in line]
    return list(set(transactions))


def print_deanonymization_stats(transactions, attempted_kernels):
    kernel_to_transactions = defaultdict(set)
    deanonymized = set()
    for transaction in transactions:
        kernels = transaction[2]
        for kernel in kernels:
            kernel_to_transactions[kernel].add(transaction)
        if len(kernels) == 1:
            deanonymized.add(kernels[0])
    total = len(set(kernel_to_transactions.keys()).intersection(attempted_kernels))
    deanon1 = len(deanonymized.intersection(attempted_kernels))
    for transaction in transactions:
        kernels = [kernel for kernel in transaction[2] if not kernel in deanonymized]
        if len(kernels) == 1:
            deanonymized.add(kernels[0])
    deanon2 = len(deanonymized.intersection(attempted_kernels))
    for transaction in transactions:
        kernels = [kernel for kernel in transaction[2] if not kernel in deanonymized]
        if len(kernels) == 1:
            deanonymized.add(kernels[0])
    deanon3 = len(deanonymized.intersection(attempted_kernels))
    print('Among filtered kernels', total, deanon1, deanon2, deanon3)


if __name__ == '__main__':
    eu_transactions = extract_transactions_from_log('aws_eu_grin-server.log.gz')
    us_transactions = extract_transactions_from_log('aws_us_grin-server.log.gz')
    he_transactions = extract_transactions_from_log('htz_eu_grin-server.log.gz')
    print(len(eu_transactions), len(us_transactions), len(he_transactions))
    eu_kernels = set()
    for tx in eu_transactions:
        for kernel in tx[2]:
            eu_kernels.add(kernel)
    us_kernels = set()
    for tx in us_transactions:
        for kernel in tx[2]:
            us_kernels.add(kernel)
    he_kernels = set()
    for tx in he_transactions:
        for kernel in tx[2]:
            he_kernels.add(kernel)
    intersection_kernels = eu_kernels.intersection(us_kernels).intersection(he_kernels)
    print(len(eu_kernels), len(us_kernels), len(he_kernels), len(intersection_kernels))
    print_deanonymization_stats(eu_transactions, eu_kernels)
    print_deanonymization_stats(us_transactions, us_kernels)
    print_deanonymization_stats(he_transactions, eu_kernels.union(us_kernels))
    print_deanonymization_stats(he_transactions, he_kernels)
    print_deanonymization_stats(eu_transactions + us_transactions + he_transactions, intersection_kernels)
    # count = sum(1 for record in eu_logs if PREFIX in record)
    # print(count, len(eu_logs))
    # kernel_sizes = defaultdict(int)
    # kernel_to_transactions = defaultdict(set)
    # for line in eu_logs:
    #     transaction = parse_logged_transaction(line)
    #     if not transaction:
    #         continue
    #     kernel_sizes[len(transaction[2])] += 1
    #     for kernel in transaction[2]:
    #         kernel_to_transactions[kernel].add(transaction)
    # print(kernel_sizes)
    # n_second_unmixings = 0
    # for kernel in kernel_to_transactions:
    #     transactions = kernel_to_transactions[kernel]
    #     if len(transactions) > 1:
    #         n_second_unmixings += 1
    # print(n_second_unmixings)
    # for block_number in range(BLOCK_START, BLOCK_FINISH):
    #     if block_number % 100 == 0:
    #         print('Block', block_number)
    #     r = requests.get('https://api-grin.blockscan.com/v1/api?module=block&action=getblock&blockno=%d' % block_number)
    #     kernels_full = r.json()['result']['kernels']
    #     kernels = [kernel['excess'] for kernel in kernels_full if kernel['features'] != 'Coinbase']
    #     for kernel in kernels:
    #         if kernel not in eu_logs:
    #             print('kernel', kernel, 'missing')
