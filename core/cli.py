import argparse
import json
from protocols.lightning_l402.mock import pay_per_request
from protocols.web_monetization.mock import pay_stream
from protocols.api_key_quota.mock import check_access
from receipt.generator import create_receipt
from core.router import choose_and_pay, choose_best_offer, simulate as run_simulate
from core.negotiation import Seller, negotiate
from core.buyer import negotiate_and_choose


def print_result(result):
    print(f"Protocol:        {result['protocol']}")
    if "mandate_id" in result:
        print(f"Mandate ID:      {result['mandate_id']}")
    if "agent_token" in result:
        print(f"Agent Token:     {result['agent_token']}")
    if "agent_credential" in result:
        print(f"Agent Credential:{result['agent_credential']}")
    if "zone" in result:
        print(f"Zone:            {result['zone']}")
    if "macaroon" in result:
        print(f"Macaroon:        {result['macaroon']}")
    if "cost_per_request" in result:
        print(f"Cost/request:    {result['cost_per_request']}")
    if "request_count" in result:
        print(f"Request count:   {result['request_count']}")
    if "rate_per_second" in result:
        print(f"Rate/second:     {result['rate_per_second']}")
    if "duration_seconds" in result:
        print(f"Duration (s):    {result['duration_seconds']}")
    print(f"Merchant:        {result['merchant']}")
    print(f"Amount:          {result['amount']}")
    if "currency" in result:
        print(f"Currency:        {result['currency']}")
    print(f"Status:          {result['status']}")
    if result["reason"]:
        print(f"Reason:          {result['reason']}")
    print(f"Transaction ID:  {result['transaction_id']}")
    print(f"Fee:             {result['fee']}")
    if "total_cost" in result:
        print(f"Total cost:      {result['total_cost']}")

    receipt = create_receipt(result)
    print()
    print("--- Receipt ---")
    print(f"Receipt ID:      {receipt['receipt_id']}")
    print(f"Issued at:       {receipt['issued_at']}")
    print(f"Signature:       {receipt['signature']}")


def main():
    parser = argparse.ArgumentParser(
        prog="paylab",
        description="Sandbox for simulating agentic multi-protocol payments"
    )
    subparsers = parser.add_subparsers(dest="command")

    simulate_parser = subparsers.add_parser("simulate", help="Simulate a payment with a protocol you choose")
    simulate_parser.add_argument("--protocol", default="x402", choices=["x402", "ap2", "mpp", "visatap", "mastercardpay", "payforcrawl"], help="Protocol to use (default: x402)")
    simulate_parser.add_argument("--merchant", default="TestMerchant", help="Merchant name")
    simulate_parser.add_argument("--amount", type=float, default=10.0, help="Payment amount")

    auto_parser = subparsers.add_parser("auto", help="Let the agent pick the best protocol on its own (lowest fee)")
    auto_parser.add_argument("--merchant", default="TestMerchant", help="Merchant name")
    auto_parser.add_argument("--amount", type=float, default=10.0, help="Payment amount")

    compare_parser = subparsers.add_parser("compare", help="Compare multiple offers, pick the lowest total cost")
    compare_parser.add_argument("--offers", required=True, help="Path to a JSON file with the list of offers")

    negotiate_parser = subparsers.add_parser("negotiate", help="Have multiple sellers negotiate against each other, pick the final lowest price")
    negotiate_parser.add_argument("--sellers", required=True, help="Path to a JSON file with the list of sellers")
    negotiate_parser.add_argument("--max-rounds", type=int, default=5, help="Maximum number of negotiation rounds (default: 5)")
    negotiate_parser.add_argument("--lambda-time", type=float, default=0.0, help="Cost of waiting per round, proportional to how uncompetitive the price is (default: 0.0 = no time cost)")

    buy_parser = subparsers.add_parser("negotiate-and-choose", help="Negotiate across many sellers, then let the AI choose among the finalists")
    buy_parser.add_argument("--sellers", required=True, help="Path to a JSON file with the list of sellers")
    buy_parser.add_argument("--preferences", default="the lowest price", help="Buyer preferences, in natural language")
    buy_parser.add_argument("--top-n", type=int, default=5, help="How many finalists to pass to the AI (default: 5)")
    buy_parser.add_argument("--max-rounds", type=int, default=30, help="Maximum negotiation rounds (default: 30)")

    stream_parser = subparsers.add_parser("stream", help="Simulate a per-request or continuous-streaming payment (Lightning L402 / Web Monetization)")
    stream_parser.add_argument("--protocol", required=True, choices=["lightning_l402", "web_monetization"], help="Which streaming/per-request protocol to use")
    stream_parser.add_argument("--merchant", default="TestMerchant", help="Merchant name")
    stream_parser.add_argument("--cost-per-request", type=float, default=0.0001, help="[lightning_l402] price per single request")
    stream_parser.add_argument("--request-count", type=int, default=1000, help="[lightning_l402] number of requests in this batch")
    stream_parser.add_argument("--rate-per-second", type=float, default=0.001, help="[web_monetization] micropayment rate per second")
    stream_parser.add_argument("--duration-seconds", type=float, default=30.0, help="[web_monetization] how long the stream ran for")

    apikey_parser = subparsers.add_parser("check-access", help="Check API key/quota access (traditional pre-paid credential model, no real-time negotiation)")
    apikey_parser.add_argument("--merchant", default="TestMerchant", help="Merchant/API provider name")
    apikey_parser.add_argument("--api-key-valid", type=lambda x: x.lower() == "true", default=True, help="Whether the API key is valid (true/false)")
    apikey_parser.add_argument("--credit-balance", type=float, default=10.0, help="Remaining pre-paid credit")
    apikey_parser.add_argument("--request-cost", type=float, default=0.01, help="Cost of this specific request")
    apikey_parser.add_argument("--rate-limit-remaining", type=int, default=100, help="Remaining requests before rate limit")

    args = parser.parse_args()

    if args.command == "simulate":
        result = run_simulate(protocol=args.protocol, merchant=args.merchant, amount=args.amount)
        print_result(result)

    elif args.command == "auto":
        outcome = choose_and_pay(merchant=args.merchant, amount=args.amount)

        print("--- Attempts ---")
        for attempt in outcome["attempts"]:
            print(f"  {attempt['protocol']:15s} status={attempt['status']:10s} fee={attempt['fee']}")
        print()

        if outcome["chosen"] is None:
            print("No protocol approved the payment.")
        else:
            print("--- Protocol chosen (lowest fee) ---")
            print_result(outcome["chosen"])

    elif args.command == "compare":
        with open(args.offers, "r") as f:
            offers = json.load(f)

        outcome = choose_best_offer(offers)

        print("--- Offers compared ---")
        for attempt in outcome["attempts"]:
            row = "  " + attempt["merchant"] + " protocol=" + attempt["protocol"] + " amount=" + str(attempt["amount"]) + " fee=" + str(attempt["fee"]) + " total=" + str(attempt["total_cost"]) + " status=" + attempt["status"]
            print(row)
        print()

        if outcome["chosen"] is None:
            print("No offer was approved.")
        else:
            print("--- Offer chosen (lowest total cost) ---")
            print_result(outcome["chosen"])

    elif args.command == "negotiate":
        with open(args.sellers, "r") as f:
            sellers_data = json.load(f)

        sellers = [Seller(lambda_time=args.lambda_time, **s) for s in sellers_data]
        outcome = negotiate(sellers, max_rounds=args.max_rounds)

        print("--- Negotiation history ---")
        for round_info in outcome["history"]:
            prices = round_info["prices"]
            top3 = sorted(prices.items(), key=lambda item: item[1])[:3]
            top3_str = ", ".join(f"{name}={price}" for name, price in top3)
            print(f"  Round {round_info['round']}: {len(prices)} sellers — top 3 cheapest: {top3_str}")
        print()

        print(f"--- Winner: {outcome['winner'].name} at {outcome['winner'].current_price} ---")

    elif args.command == "negotiate-and-choose":
        with open(args.sellers, "r") as f:
            sellers_data = json.load(f)

        sellers = [Seller(**s) for s in sellers_data]

        result = negotiate_and_choose(
            sellers,
            buyer_preferences=args.preferences,
            top_n=args.top_n,
            max_rounds=args.max_rounds,
        )

        print(f"--- Top {args.top_n} finalists ---")
        for s in result["finalists"]:
            print(f"  {s.name}: {s.current_price} (strategy: {s.strategy})")

        print()
        print("--- Final choice (AI) ---")
        print(f"Merchant:    {result['chosen_merchant']}")
        print(f"Reasoning:   {result['reasoning']}")

    elif args.command == "stream":
        if args.protocol == "lightning_l402":
            result = pay_per_request(
                merchant=args.merchant,
                cost_per_request=args.cost_per_request,
                request_count=args.request_count,
            )
        elif args.protocol == "web_monetization":
            result = pay_stream(
                merchant=args.merchant,
                rate_per_second=args.rate_per_second,
                duration_seconds=args.duration_seconds,
            )

        print_result(result)

    elif args.command == "check-access":
        result = check_access(
            merchant=args.merchant,
            api_key_valid=args.api_key_valid,
            credit_balance=args.credit_balance,
            request_cost=args.request_cost,
            rate_limit_remaining=args.rate_limit_remaining,
        )

        print(f"Protocol:          {result['protocol']}")
        print(f"Merchant:          {result['merchant']}")
        print(f"HTTP Status:       {result['http_status_code']}")
        print(f"Status:            {result['status']}")
        if result["reason"]:
            print(f"Reason:            {result['reason']}")
        print(f"Request cost:      {result['request_cost']}")
        print(f"Remaining credit:  {result['remaining_credit']}")
        print(f"Transaction ID:    {result['transaction_id']}")

        receipt = create_receipt(result)
        print()
        print("--- Receipt ---")
        print(f"Receipt ID:      {receipt['receipt_id']}")
        print(f"Issued at:       {receipt['issued_at']}")
        print(f"Signature:       {receipt['signature']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()