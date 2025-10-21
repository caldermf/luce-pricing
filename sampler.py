import random
from collections import defaultdict
import logging
import math
from itertools import combinations
import cvxpy as cp
import numpy as np
import pandas as pd

# Helper functions
def dict_to_list(pool):
    return list(pool.keys()), list(pool.values())

def weighted_sample_without_replacement(population, weights, k):
    sample = []
    
    if k > len(population):
        raise ValueError("Sample size k cannot be greater than the population size.")
    
    population_copy = population[:]
    weights_copy = weights[:]

    for _ in range(k):
        selected = random.choices(population_copy, weights=weights_copy, k=1)[0]
        sample.append(selected)
        index = population_copy.index(selected)
        del population_copy[index]
        del weights_copy[index]
    
    return sample

def print_dictionary(d):
    for key, value in d.items():
        # handle None or non-numeric values safely
        if value is None:
            print(f"{key}: None")
        else:
            try:
                print(f"{key}: {value:.4f}")
            except Exception:
                print(f"{key}: {value}")

###############################################################################
############### code for sampling permutations based on weights ###############
###############################################################################

def get_ordering_frequency(population, weights, iterations):
    table = defaultdict(int)
    size = len(population)

    for _ in range(iterations):
        ord = tuple(weighted_sample_without_replacement(population, weights, size)) # sample an ordering
        table[ord] += 1
    return table

def get_ordering_distribution(population, weights, iterations, normalize=True):
    table = get_ordering_frequency(population, weights, iterations)
    
    # normalize the table to get probabilities
    if normalize:
        for ord in table:
            table[ord] /= iterations

    return table

def probability_of_show(horse, table):
    total_prob = 0
    for perm, prob in table.items():
        if horse in perm[:3]:
            total_prob += prob
    return total_prob

def get_show_table(pool, iterations=100000):
    population, weights = dict_to_list(pool)
    table = get_ordering_distribution(population, weights, iterations)
    results = {}
    for element in population:
        results[element] = probability_of_show(element, table)

    return results

def get_show_distribution_with_payout(pool: dict, show_pool: dict, iterations: int = 100000) -> tuple[dict, dict]:
    """Given win pool, show pool and number of iterations, returns the distribution over show outcomes as well as a vector of profits"""
    population, weights = dict_to_list(pool)
    _, show_weights = dict_to_list(show_pool)
    total_show_pool = sum(show_weights)
    table = get_ordering_distribution(population, weights, iterations)
    show_prob_dict = {}
    show_gain_dict = {}
    all_show_combo = list(combinations(population, 3))
    for show in all_show_combo:
        total_prob = 0
        show_set = set(show)
        for perm, prob in table.items():
            if show_set == set(perm[:3]):
                total_prob += prob
        gain_dict = {}
        total_winnings = total_show_pool*0.8 # takeout assumed to be $20%
        for horse in show:
            total_winnings -= show_pool[horse]
        winnings_per_horse = total_winnings/3

        for horse in population:
            if horse in show_set:
                gain_dict[horse] = winnings_per_horse/show_pool[horse]
            else:
                gain_dict[horse] = -1.0
        
        show_prob_dict[show] = total_prob
        show_gain_dict[show] = gain_dict

    
    return show_prob_dict, show_gain_dict 



###############################################################################
########################## code for comparing tables ##########################
###############################################################################

def get_probability_table(pool, iterations=100000):
    population, weights = dict_to_list(pool)
    return get_ordering_distribution(population, weights, iterations)

def get_relative_pool(base_pool):
    relative_pool = {}
    total = sum(base_pool.values())
    if total == 0:
        logging.warning("Total weight of base_pool is zero; returning zeros for relative pool.")
        for element in base_pool:
            relative_pool[element] = 0.0
        return relative_pool

    for element, weight in base_pool.items():
        relative_pool[element] = weight / total
    return relative_pool

# compute expected winnings and expected winnings given win based on parimutuel payouts for show
def get_parimutuel_payout(pool, ordering_prob, show_pool):
    population, weights = dict_to_list(pool)
    parimutuel_payout = defaultdict(float)
    parimutuel_payout_given_win = defaultdict(float)
    total_show_pool = sum(show_pool.values())

    for candidate in population:
        payout = 0
        payout_given_win = 0
        prob_win = 0
        for ord, prob in ordering_prob.items():
            if candidate not in ord[:3]:
                continue

            top3_total = sum(show_pool[horse] for horse in ord[:3])
            if top3_total <= 0:
                continue
            
            prob_win += prob ################ TODO: THIS IS WRONG!
            payout += (total_show_pool / top3_total) * prob # this computes expected *total return* not just winnings
            payout_given_win += (total_show_pool / top3_total) * prob # this computes expected *total return* given win
        parimutuel_payout[candidate] = payout - 1 # subtract the 1 you bet to get expected winnings
        if prob_win > 0:
            parimutuel_payout_given_win[candidate] = (payout_given_win / prob_win) - 1
        else:
            parimutuel_payout_given_win[candidate] = -1 # if horse cannot win, expected winnings given win is -1 (you lose your bet)
    return parimutuel_payout, parimutuel_payout_given_win

def get_odds_payout(pool, ordering_prob, odds): # odds is a dict of horse -> odds (e.g., 4 means you win 4 for every 1 you bet)
    population, weights = dict_to_list(pool)
    odds_payout = defaultdict(float)

    for candidate in population:
        payout = 0
        for ord, prob in ordering_prob.items():
            if candidate not in ord[:3]:
                continue

            payout += odds[candidate] * prob # this computes expected *winnings* not total return
        
        odds_payout[candidate] = payout

    return odds_payout

def get_projected_expectation(pool, method='parimutuel', iterations=100000, show_pool=None, odds=None):
    expectation = defaultdict(float)
    population, weights = dict_to_list(pool)
    ordering_prob = get_ordering_distribution(population, weights, iterations)

    if method == 'parimutuel':
        if show_pool is None:
            raise ValueError("show_pool must be provided for parimutuel method.")
        expectation, expectation_given_win = get_parimutuel_payout(pool, ordering_prob, show_pool) ####### TODO: THIS IS WRONG!

    elif method == 'odds':
        if odds is None:
            raise ValueError("odds must be provided for odds method.")
        expectation = get_odds_payout(pool, ordering_prob, odds)

    else:
        raise ValueError("Method must be either 'parimutuel' or 'odds'.")
    
    return dict(expectation)

def get_projected_expectation_on_win(pool, method='parimutuel', iterations=100000, show_pool=None, odds=None):
    expectation_given_win = defaultdict(float)
    population, weights = dict_to_list(pool)
    ordering_prob = get_ordering_distribution(population, weights, iterations)

    if method == 'parimutuel':
        if show_pool is None:
            raise ValueError("show_pool must be provided for parimutuel method.")
        _, expectation_given_win = get_parimutuel_payout(pool, ordering_prob, show_pool) ###### TODO: THIS IS WRONG!

    elif method == 'odds':
        if odds is None:
            raise ValueError("odds must be provided for odds method.")
        # For odds method, expected winnings given win is simply the odds
        for horse in population:
            expectation_given_win[horse] = odds[horse]

    else:
        raise ValueError("Method must be either 'parimutuel' or 'odds'.")
    
    return dict(expectation_given_win)

def optimize_show_portfolio(show_prob_dict, show_gain_dict, population, L=1.0, fmax=0.25, epsilon=0.0, solver="ECOS"):
    """
    Maximize:   sum_omega pi[omega] * log( 1 + sum_i f_i * r_{i,omega} )
    s.t.:       0 <= f_i <= fmax,  sum_i f_i <= L,  and 1 + sum_i f_i * r_{i,omega} >= epsilon  for all omega

    Assumes:
      - show_prob_dict[omega] is float and ~sums to 1.
      - show_gain_dict[omega][horse] is float net return r_{i,omega} for every horse in population.
      - population is an iterable of horse IDs (hashable).
    Returns:
      - f_dict: {horse -> optimal fraction}
      - info:   diagnostics dict
    """
    horses = list(population)
    omegas = list(show_prob_dict.keys())

    # Build π and R
    pi = np.array([show_prob_dict[w] for w in omegas], dtype=float)            # (m,)
    s = float(pi.sum())
    if s <= 0:
        raise ValueError("Sum of probabilities must be positive.")
    pi = pi / s  # light normalize

    R = np.array([[float(show_gain_dict[w][h]) for h in horses]                # (m, n)
                  for w in omegas], dtype=float)

    n = len(horses)
    f = cp.Variable(n, nonneg=True)
    aff = 1 + R @ f

    objective = cp.Maximize(pi @ cp.log(aff))
    constraints = [
        f <= fmax,
        cp.sum(f) <= L,
        aff >= epsilon
    ]

    prob = cp.Problem(objective, constraints)
    prob.solve(solver=solver)

    if f.value is None:
        raise RuntimeError(f"Optimization failed (status: {prob.status}).")

    f_vec = np.clip(f.value, 0.0, None)
    f_dict = {h: round(x, 4) for h, x in zip(horses, f_vec)}

    # simple diagnostics
    aff_val = 1 + R @ f_vec
    info = {
        "status": prob.status,
        "expected_log_growth": float(np.dot(pi, np.log(aff_val))),
        "worst_case_wealth_multiplier": float(aff_val.min()),
        "sum_f": float(f_vec.sum()),
    }

    return f_dict

def run_analysis(pool: dict, show_pool: dict, print_data: bool = True) -> dict:

    population, _ = dict_to_list(pool)

    show_prob_dict, show_gain_dict = get_show_distribution_with_payout(pool, show_pool)
    all_show_combo = list(combinations(population, 3))

    f_opt = optimize_show_portfolio(show_prob_dict, show_gain_dict, population)

    return f_opt

'''
def run_analysis(pool, show_pool, print_data : bool = True) -> list:
    # If the show pool sums to zero, cancel analysis and explain to the user.
    total_show_pool = sum(show_pool.values()) if show_pool else 0
    if total_show_pool == 0:
        print("Show pool total is 0. The parimutuel projected earnings cannot be computed because there is no money in the show pool.")
        print("This usually means the snapshot did not contain valid pool data (e.g., all entries had None), or the bookmaker returned zeros.")
        return []
    
    relative_show_pool = get_relative_pool(show_pool)

    show_table = get_show_table(pool, 100000)

    projected_exp = get_projected_expectation_on_win(pool, method='parimutuel', iterations=100000, show_pool=show_pool)
    ################## TODO: THIS IS WRONG!

    bets = []
    log_growth = []
    for horse, exp in projected_exp.items():
        kelly_fraction = show_table[horse] - (1 - show_table[horse]) / (exp * 0.8)
        if kelly_fraction > 0:
            bets.append({"horse": horse, "bet_size": kelly_fraction/4}) # use 1/4 kelly
            log_growth.append({"horse": horse, "value": show_table[horse]* math.log( 1 + kelly_fraction*projected_exp[horse] ) + (1-show_table[horse])*math.log(1-kelly_fraction) })
    
    ### strategy is chosen here. TODO: separate

    max_log_growth = 0 # choose a single horse base on max expected log-growth
    chosen_horse = None
    for h in log_growth:
        if h["value"] > max_log_growth:
            max_log_growth = h["value"]
            chosen_horse = h["horse"]
    
    for bet in bets:
        if bet["horse"] == chosen_horse:
            bets = [ {"horse": bet["horse"], "bet_size": bet["bet_size"]} ] 
            break

    if print_data:
        print("Relative Show Pool Distribution:")
        print("-")
        print_dictionary(relative_show_pool)
        print("---")
        print("Projected Show Probabilities:")
        print("-")
        print_dictionary(show_table)
        print("---")
        print("Projected Expected Earnings on Win (Parimutuel - with 20% takeout):")
        print("-")
        for horse, exp in projected_exp.items():
            print(f"{horse}: {(0.8*exp):.4f}")
        print("---")

    return bets
'''


###########################################################################
###################### Code for importing jsonl data ######################
###########################################################################

def jsonl_to_dicts(filename):
    import json
    dicts = []
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            dicts.append(json.loads(line))
    return dicts

def snapshot_to_pools(snapshot):
    win_pool = {}
    show_pool = {}
    for entry in snapshot['entries']:
        horse = entry['horse']
        if entry['win_pool'] is None or entry['show_pool'] is None:
            continue
        else:
            win_pool[horse] = entry['win_pool']
            show_pool[horse] = entry['show_pool']
    return win_pool, show_pool






if __name__ == "__main__":
    snapshots = jsonl_to_dicts("live_odds_snapshots.jsonl")
    latest_snapshot = snapshots[-1]

    win_pool, show_pool = snapshot_to_pools(latest_snapshot)

    print(f"Track: {latest_snapshot['track']}, Race Number: {latest_snapshot['race_number']}")

    run_analysis(win_pool, show_pool)
