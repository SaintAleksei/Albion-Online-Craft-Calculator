#!/usr/bin/python3

import yaml
import pd
import numpy as np
import argparse
import sys
import os

# TODO Tests
# TODO Unix-like interface
# TODO Doc-strings
# TODO CSVTable types
# TODO Change CSVTable to Pandas Data Frame

# Global constants, gathered dierctly from game
g_const =\
{
  # Tiers
  'min_tier': 4,
  'max_tier': 8,
  # Enchantments
  'min_ench': 0,
  'max_ench': 4,
  # Item value to food convertation coefficient
  'item_value2food': 0.1125,
  # Coeffs to compute resource item value'
  'res_item_value_base': 2,
  'res_item_value_coeff': 2,
  # Coeffs to compute fame
  'base_fame_coeffs': [22.5, 90, 270, 645, 1395],
  'fame_factor': 2,
  # Premium bonus coefficient
  'premium_bonus': 1.5,
  # Coeffs to compute focus cost from focus efficienty
  'focus_cost_coeff': 2,
  'focus_cost_divider': 10000,
  # Royal artifacts ammount per slot and tier
  'royal': 
  {
    'head': [4, 8, 16, 16, 16],
    'body': [2, 4,  8,  8,  8],
    'legs': [2, 4,  8,  8,  8],
  },
  # Journals fame coeffs
  'fame_per_journal': [0, 0, 0, 3600, 7200, 14400, 28380, 58590],
  # List of supported slots
  'slots': ['head', 'body', 'legs', 'right-hand', 'left-hand', 'two-handed'],
  # Coeff to compute artifact item values 
  'art_item_value_coeff': 2,
}

def yaml_load(fname):
  data = None
  with open(fname) as f:
    data = yaml.full_load(f)
  return data

def die(message):
  raise RuntimeError(message)

# Main class for armor, weapons and off-hands crafting calculations
# TODO Should be generalized to ALL game items
class Recipe:
  '''Item craft recipe'''

  base_focus_cost = None
  artifact_focus_cost = None

  @classmethod
  def configure(cls, base_focus_cost=None, artifact_item_values=None):
    if base_focus_cost is not None:
      cls.base_focus_cost = base_focus_cost
    if artifact_item_values is not None:
      cls.artifact_item_values = artifact_item_values
  
  def __init__(self, *, name, resources, artifact, is_royal,
               slot, machine, family):
    '''Init Recipe'''
    # Tested
    self.name      = name
    self.artifact  = artifact
    self.is_royal  = is_royal
    self.resources = resources
    self.slot      = slot
    self.machine   = machine
    self.family    = family

  def cost_price(self, tier, ench, resources,
                 artifacts=None, tax=0, retrate=0):
    # Tested
    '''Calculate cost price'''
    result = 0.0
    res_prices = resources[(resources['tier'] == tier) & (resources['ench'] == ench)]
    if len(res_prices.index) > 1:
      raise ValueError(f'Bad resources table: duplicated value of \'{tier}.{ench}\'')
    for name, amount in self.resources.items():
      cost = res_prices.get(name, None)
      try:
        cost = int(cost)
      except ValueError:
        print(err_no_data)  
        return None

      result += cost * amount

    # Taking resource return rate into account
    result *= 1 - retrate

    # Add Artifacts and Royals
    if self.artifact != 'None':
      art_prices = artifacts[artifacts['tier'] == tier]
      if len(art_prices.index) > 1:
        raise ValueError(f'Bad artifacts table: duplicated value of \'{tier}\'')
      art_cost = art_prices.get(self.artifact, None)
      try:
        art_cost = int(art_cost)
      except TypeError:
        print(err_no_data)
        return None

      art_amount = 1
      if self.is_royal:
        art_amount = g_const['royal'][self.slot][tier-g_const['min_tier']]

      result += art_amount * art_cost

    # Taking into account taxes
    result += g_const['item_value2food'] * self.item_value(tier, ench) / 100 * tax

    try:
      result = int(result)
    except:
      result = None

    return result

  def item_value(self, tier, ench):
    # Tested
    '''Calculate item value'''
    # Arguments validation
    resource_item_value = g_const['res_item_value_base'] * g_const['res_item_value_coeff'] ** (tier + ench - 1)
    # Resources item value
    result = sum(self.resources.values()) * resource_item_value  

    # Artifact and Royal item value
    if self.artifact != 'None':
      if self.artifact_item_values is None:
        die(f'{type(self) not configured: artifact_item_values is required')
      art_item_values = self.artifact_item_values['item_value']
      base_item_value = art_item_values.get(self.artifact, None)
      if base_item_value is None:
        die(f'Can\'t get item value of \'{self.artifact}\' from config')
      idx = tier - g_const['min_tier']
      factor = g_const['art_item_value_coeff'] ** idx
      art_item_value = base_item_value * factor
      art_amount = 1
      if self.is_royal:
        art_amount = g_const['royal'][self.slot][idx]
      result += art_amount * int(art_item_value)

    return int(result)

  def fame(self, tier, ench):
    '''Calculate fame'''
    # Tested
    tier, ench = assert_tier_ench(tier, ench)
    idx = tier - g_const['min_tier']
    base_fame = g_const['base_fame_coeffs'][idx] * sum(self.resources.values())
    result = base_fame * g_const['fame_factor'] ** ench

    return int(result)

  def compute_masteries(self, masteries_cfg, masteries):
    # TODO Test it
    family_masteries = masteries.get(self.family, None)
    if family_masteries is None:
      print('Can\'t compute masteries for \'{self.name}\': family masteries is required')
      return None, None
  
    family_masteries_cfg = masteries_cfg.get(self.family, None)
    if family_masteries_cfg is None:
      print('Can\'t compute masteries for \'{self.name}\': family masteries config is required')
      return None, None

    focus_efficienty = 0
    quality = 0
    for name, coeff in family_masteries.items()
      mastery_cfg = family_masteries_cfg.get(name, None)
      if mastery_cfg is None:
        print('Can\'t compute masteries for \'{self.name}\': \'{name}\' mastery config is required')
        return None, None

      if name == self.name:
        focus_efficienty += coeff * (mastery_cfg['own_eff'] + mastery['comm_eff'])
        quality += coeff * (mastery_cfg['own_qual'] + mastery['comm_qual'])
      else:
        focus_efficienty += coeff * mastery_cfg['comm_eff']
        quality += coeff * mastery_cfg['comm_qual']

    return focus_efficienty, quality
       
  def focus_cost(self, tier, ench, focus_efficiency):
    # TODO Test it
    df = self.base_focus_cost
    if dfs is None:
      die(f'{type(self) not configured: base_focus_cost is required')

    base_costs_list = df[(df['tier'] == tier) & (df['ench'] == ench)]
    base_cost = base_costs_list.get(self.slot, None)
    if base_cost is None:
      die(f'Can\'t get base focus cost for \'{self.slot} {tier}.{ench}\' from config')

    power = focus_efficiency / g_const['focus_cost_divider']
    denominator = g_const['focus_cost_coeff'] ** power
    cost = base_cost / denominator

    return int(cost)

  def requirements(self, amount, retrate):
    # Tested
    def resources2amount(resources, res_per_item, retrate):
      resources = int(resources)
      res_per_item = int(res_per_item)
      amount = 0
      while resources >= res_per_item:
        num = int(resources / res_per_item) 
        resources -= num * res_per_item
        resources += int(retrate * num * res_per_item)
        amount += num

      return amount, resources

    result = {}
    for res_name, res_amount in self.resources.items():
      start = int(res_amount * amount * retrate) - res_amount
      end = int(res_amount * amount * retrate) + res_amount
      for res_amt in range(start, end+1):
        amt, rest = resources2amount(res_amt, res_amount, retrate)
        if amt == amount:
          result[res_name] = res_amt
          break

    return result

  def quality(self, quality)
    # TODO Haven't found info about it yet
    # Here should be some code, that converts quality to chances
    raise NotImplementedError

class Crafter:
  def __init__(self, *,\
               resources, artifacts=None,\
               config='config',\
               tax=0, retrate=0,\
               item_prices=None,\
               masteries=None,\
               journals_bying=None, journals_selling=None):
    '''Doc'''
    # Configuration
    base_focus_cost      = pd.read_csv(os.path.join(config, 'base_focus_cost.csv'))
    artifact_item_values = pd.read_csv(os.path.join(config, 'artifact_item_values.csv'))
    Recipe.configure(base_focus_cost, artifact_item_values)
    self.recipes = {}
    recipes_file = yaml_load(os.path.join(config, 'recipes.yaml'))
    for machine, families in recipes_file.items():
      for family, items in families.items():
        for name, attributes in items.items():
          resources = attributes['resources']
          slot = attributes['slot']
          artifact = attributes.get('artifact', None)
          is_royal = attributes.get('is_royal', None)
        
          self.recipes[name] = Recipe(name=name,\
                                      resources=resources,\
                                      machine=machine,\
                                      family=family,\
                                      artifact=artifact,\
                                      is_royal=is_royal,\
                                      slot=slot)
    self.masteries_cfg = yaml_load(os.path.join(config, 'masteries_cfg.yaml'))

    # Calculations
    self.data = pd.DataFrame()
    self.data['name']             = pd.Series(dtype=object)
    self.data['cost_price']       = pd.Series(dtype=object)
    self.data['fame']             = pd.Series(dtype=object)
    self.data['focus']            = pd.Series(dtype=object)
    self.data['journals_amount']  = pd.Series(dtype=object)
    if journals_buying is not None and journals_selling is not None:
      self.data['journals_buying']  = pd.Series(dtype=object)
      self.data['journals_selling'] = pd.Series(dtype=object)
    if item_prices is not None:
      self.data['sell_price']       = pd.Series(dtype=object)
      self.data['absolute_profit']  = pd.Series(dtype=object)
      self.data['relative_profit']  = pd.Series(dtype=object)
      self.data['profit_per_focus'] = pd.Series(dtype=object)

    for name, recipe in self.recipes.items():
      for tier in range(g_const['min_tier'], g_const['max_tier'] + 1):
        for ench in range(g_const['min_ench'], g_const['max_ench'] + 1):
          result = {}
          result['name'] = f'{name} {tier}.{ench}'
          result['cost_price'] = recipe.cost_price(tier, ench, resources,\
                                                   artifacts, tax, retrate)
          focus_eff, qual = recipe.compute_masteries(self.masteries_cfg, masteries)
          result['focus'] = recipe.focus_cost(tier, ench, focus_eff)
          result['fame'] = recipe.fame(tier, ench)
          result['journals_amount'] = result['fame'] / g_const['fame_per_journal']
          if journals_buying is not None and journals_selling is not None:
            df = journals_buying
            result['journals_buying'] = df[df['tier'] == tier].get(recipe.machine, np.NAN)
            df = journals_selling
            result['journals_selling'] = df[df['tier'] == tier].get(recipe.machine, np.NAN)
          if item_prices is not None:
            df = item_prices
            sell_price = df[df['tier'] == tier & df['ench'] == ench].get(name, np.NAN)
            cost_price = result['cost_price']
            j_sell = result['journals_selling']
            j_buy = result['journals_buying']
            result['absolute_profit'] = sell_price + j_sell - cost_price - j_buy
            result['relative_profit'] = result['absolute_profit'] / (cost_price + j_buy)
            result['profit_per_focus'] = result['absolute_profit'] / result['focus']
          result = pd.DataFrame([result])
          self.data = pd.concat([self.data, result], ignore_index=True)
          
  def analyze(self, *, tiers=None, enchs=None, items=None, sort_by=None
              profit_per_focus=None, absolute_profit=None, realtive_profit=None):
    pass

  def calculate(self, *, name, amount=1):
    pass
      
  return price_table, fame_table, focus_table

def test_case(test_dir):
  resources = pd.read_csv(os.path.join(test_dir, 'test_resources.csv'))
  artifacts = pd.read_csv(os.path.join(test_dir, 'test_artifacts.csv'))
  test      = pd.read_csv(os.path.join(test_dir, 'test_results.csv'))
  test_params = yaml_load(os.path.join(test_dir, 'test_params.yaml'))
  recipe_dict = yaml_load(os.path.join(test_dir, 'test_recipe.yaml'))
  req         = yaml_load(os.path.join(test_dir, 'test_requirements.yaml'))
  recipe = Recipe(**recipe_dict)

  for index, row in test.iterrows()
    tier, ench = row.split('.')
    cost_price = recipe.cost_price(tier, ench, resources, **test_params))
    fame = recipe.fame(tier, ench))
    item_value = recipe.item_value(tier, ench))
    true_results = row
    if int(true_results['fame']) - fame > 1 or\
       int(true_results['item_value']) - item_value > 1 or\
       int(true_results['cost_price']) - cost_price > 1:
      print(f'Test failed at \'{row}\'')
      print(f'\tcost_price = {cost_price} (expected {true_results["cost_price"]})')
      print(f'\tfame       = {fame} (expected {true_results["fame"]})')
      print(f'\titem_value = {item_value} (expected {true_results["item_value"]})')
      return False

  if req is not None:
    res_amt = req['res_amount']
    retrate = req['retrate']
    items_amt = req['items_amount']
    res_amt_to_test = recipe.requirements(items_amt, retrate)
    for name, amt in res_amt_to_test.items():
      if amt != res_amt[name]:
        print(f'Test failed at requirements \'{name}\'\n')
        print(f'\tres_amt[{name}] = {amt} (expected {res_amt[name]})\n')
      return False
  
  # TODO Add materies and focus_cost tests

  return True

def main():
  if Recipe.test_case('tests'):
    print('Test in \'tests\' succeed\n')
  else:
    print('Test in \'tests\' failed\n')

  parser = argparse.ArgumentParser()
  parser.add_argument("tax", help="Machine's tax", type=int)
  parser.add_argument("retrate", help="Resource return rate", type=float)
  args = parser.parse_args()


  recipes = read_recipes('config/recipes.yaml')
  resources = CSVTable()
  resources.read('resources.csv')
  artifacts = CSVTable()
  artifacts.read('artifacts.csv')

  price_table, fame_table, focus_table = compute_recipes(recipes,\
                                                         resources,\
                                                         args.tax,\
                                                         args.retrate,\
                                                         artifacts)

  price_table.write('prices.csv')
  fame_table.write('fame.csv')
  focus_table.write('focus.csv')

# ao-tool 
#   craft 
#     analyze 
#       --items '' 
#       --sort-by '' 
#       --absolute-profit '' 
#       --relative-profit '' 
#       --profit-per-focus '' 
#       --resources ''
#       --artifacts ''
#       --item-prices ''
#       --journals-buying ''
#       --journals-selling ''
#       --masteries ''
#       --config ''
#       --tax ''
#       --retrate ''
#       task_file
#     calculate
#       --name ''
#       --tax ''
#       --retrate ''
#       --amount ''
#       --resources ''
#       --artifacts ''
#       --item-prices ''
#       --journals-buying ''
#       --journals-selling ''
#       --masteries ''
#       --config ''
#       task_file

if __name__ == '__main__':
  main()
