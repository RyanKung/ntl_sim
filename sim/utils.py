import operator
from .netrual import NLT_reserve, NLT_components, NLT_accounts


def highest(market_prices: dict):
    return max({
        t: float(p) * NLT_components[t].min_bid

        for t, p in market_prices.items()
        if t != 'timestamp'
    }.items(), key=operator.itemgetter(1))


def lowest(market_prices: dict):
    return min({
        t: float(p) * NLT_components[t].min_bid
        for t, p in market_prices.items()
        if t != 'timestamp'
    }.items(), key=operator.itemgetter(1))


def get_profit_pair(market_prices, threshold=0.001):
    highest_component, highest_value = highest(market_prices)
    lowest_component, lowest_value = lowest(market_prices)
    if float(highest_value) / float(lowest_value) < (1 + threshold):
        return False
    return {
        'from': NLT_components[lowest_component],
        'to': NLT_components[highest_component],
        'rate': highest_value / lowest_value
    }


def exchange(market_prices, ts, sender):
    pair = get_profit_pair(market_prices)
    assert pair['from'](ts).auction(sender, pair['from'].min_bid * pair['rate'])
    pair['to'](ts).redeem(sender, 1000)


def nlt_price_2(market_price: dict):
    if NLT_components['EOS'].total_supply == 0:
        return nlt_price(market_price) * 10
    return sum([market_price[t] * v for t, v in NLT_reserve.items()]) / float(len(NLT_components) * 1000)

    # h = highest(market_prices)
    # return (market_prices[h] * NLT_reserve[h])


def nlt_price(market_price: dict):
    h = highest(market_price)[0]
    return (market_price[h] * NLT_components[h].min_bid) / 1000
    # total_supply = list(NLT_components.values())[0].total_supply
    # return nlt_value(market_price) / total_supply


def profit_rate(p_c, p_nlt, min_bid):
    value_c = min_bid * p_c
    value_nlt = p_nlt * 1000
    return float(value_c) / float(value_nlt)


def auction_threshold(p_c, p_nlt, min_bid):
    profit = profit_rate(p_c, p_nlt, min_bid)
    return 1 / profit > 1.0001


def redeem_threshold(p_c, p_nlt, min_bid):
    profit = profit_rate(p_c, p_nlt, min_bid)
    return profit > 1.0001


def get_worth_to_auction(market_price: dict, price_model=nlt_price, threshold_func=auction_threshold):
    price = price_model(market_price)
    return {
        k: {
            'price': v,
            'min_bid': NLT_components[k].min_bid,
            'delta': price * 1000 - v * NLT_components[k].min_bid
        }
        for k, v in market_price.items()
        if threshold_func(v, price, NLT_components[k].min_bid)
    }


def get_worth_to_redeem(market_price: dict, price_model=nlt_price, threshold_func=redeem_threshold):
    price = price_model(market_price)
    return {
        k: {
            'price': v,
            'min_bid': NLT_components[k].min_bid,
            'delta': v * NLT_components[k].min_bid - price * 1000
        }
        for k, v in market_price.items()
        if threshold_func(v, price, NLT_components[k].min_bid)
    }


def determin_auction_quantity(market_price: dict, price_model=nlt_price):
    price = price_model(market_price)

    planned = {
        k: price * 1000 / v['price']
        for k, v
        in get_worth_to_auction(market_price).items()
    }
    return {
        k: v
        for k, v
        in planned.items()
        if v >= NLT_components[k].min_bid
    }


def determin_redeem_quantity(market_price: dict, price_model=nlt_price):
    # redeemed = self.reserve / self.total_supply * quantity
    price = price_model(market_price)

    def quantity(token, t_price, n_price):
        q = 1000
        while NLT_components[token].get_redeem_amount(q) * t_price > n_price * q:
            q += 1000
        return q

    planned = {
        k: quantity(k, v['price'], price)
        for k, v
        in get_worth_to_auction(market_price).items()
    }

    return {
        k: v
        for k, v in planned.items()
        if v != 0
    }


def check_status():
    return {k: v.minted for k, v in NLT_components.items()}


def check_min_bid():
    return {k: v.min_bid for k, v in NLT_components.items()}


def redeem(token, market_price, sender, rate=0.002):
    balance = NLT_accounts.get(sender, float(0))
    return NLT_components[token].redeem(sender, balance * rate)


def redeem_strategy(plan: dict, sender: str, ts: int):
    return {
        'redeemed': NLT_components[t](ts).redeem(sender, q)
        for t, q in plan.items()
    }


def auction_strategy(plan: dict, sender: str, ts: int):
    return {
        'auctioned': NLT_components[t](ts).auction(sender, bid)
        for t, bid in plan.items()
    }
