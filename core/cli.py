import argparse
import json
from protocols.x402.mock import pay as pay_x402
from protocols.ap2.mock import pay as pay_ap2
from protocols.mpp.mock import pay as pay_mpp
from protocols.visatap.mock import pay as pay_visatap
from protocols.mastercardpay.mock import pay as pay_mastercardpay
from protocols.payforcrawl.mock import pay as pay_payforcrawl
from receipt.generator import create_receipt
from core.router import choose_and_pay, choose_best_offer
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

    buy_parser = subparsers.add_parser("negotiate-and-choose", help="Negotiate across many sellers, then let the AI choose among the finalists")
    buy_parser.add_argument("--sellers", required=True, help="Path to a JSON file with the list of sellers")
    buy_parser.add_argument("--preferences", default="the lowest price", help="Buyer preferences, in natural language")
    buy_parser.add_argument("--top-n", type=int, default=5, help="How many finalists to pass to the AI (default: 5)")
    buy_parser.add_argument("--max-rounds", type=int, default=30, help="Maximum negotiation rounds (default: 30)")

    args = parser.parse_args()

    if args.command == "simulate":
        if args.protocol == "x402":
            result = pay_x402(merchant=args.merchant, amount=args.amount)
        elif args.protocol == "ap2":
            result = pay_ap2(merchant=args.merchant, amount=args.amount)
        elif args.protocol == "mpp":
            result = pay_mpp(merchant=args.merchant, amount=args.amount)
        elif args.protocol == "visatap":
            result = pay_visatap(merchant=args.merchant, amount=args.amount)
        elif args.protocol == "mastercardpay":
            result = pay_mastercardpay(merchant=args.merchant, amount=args.amount)
        elif args.protocol == "payforcrawl":
            result = pay_payforcrawl(merchant=args.merchant, amount=args.amount)

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

        sellers = [Seller(**s) for s in sellers_data]
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

    else:
        parser.print_help()


if __name__ == "__main__":
    main()