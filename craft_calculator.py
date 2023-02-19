#!/usr/bin/python3

from csvtable import CSVTable
import yaml
import numpy as np

# TODO Tests
# TODO Unix-like interface

# Global constants
g_const 
{
  'min_tier': 4,
  'max_tier': 8,
  'min_ench': 0,
  'max_ench': 3,
  'item_value2food': 0.1125,
  'res_item_value_base': 2,
  'res_item_value_coeff': 2,
  'base_fame_coeffs': [22.5, 90, 270, 645, 1395],
  'royal_fame_coefffs': [2.5, 5, 10, 10, 10],
  'premium_bonus': 1.5,
  'focus_cost_coeff': 2,
  'focus_cost_divider': 10000,
  'royal': 
  {
    'head': [4, 8, 16, 16, 16],
    'body': [2, 4,  8,  8,  8],
    'legs': [2, 4,  8,  8,  8],
  },
  'fame_per_journal': [3600, 7200, 14400, 28380, 58590]
  'slots': ['head', 'body', 'legs', 'right-hand', 'left-hand', 'two-handed'],
  'artifact_item_value_coeff': 2,
  'base_mastery_eff': 30,
  'base_mastery_qual': 0.75,
  'main_mastery_eff': 250,
  'main_mastery_qual': 6,
}


# Helpfull functions, maybe will be restructed in future
def assert_tier_ench(tier, ench):
  tier = int(tier)
  ench = int(ench)
  if not g_const['min_tier']  <= tier <= g_const['max_tier']
    raise ValueError('Bad tier')
  if not g_const['min_ench'] <= ench <= g_const['max_tier']
    raise ValueError('Bad enchantment level')

  return tier, ench

# TODO Maybe name can be recived from obj
def assert_type(obj, name, type2check, *, convert=True):
  if type(obj) == type2check:
    return obj

  if not convert:
    raise TypeError(f'Bad type of \'{name}\', {type2check} is required')

  try: 
    obj = type2check(obj)
  except:
    raise TypeError(f'Can\'t convert \'{name}\' to {type2check}')
  else
    return obj

def yaml_load(fname):
  data = None
  with open(fname) as f:
    data = yaml.full_load(f)
  return data

def die(message):
  print(message)
  print('Fatal error; can\'t continue work')
  exit(1)

# Main class for armor, weapons and off-hands crafting calculations
# TODO Should be generalized to ALL game items
class Recipe:
  '''Item craft recipe'''
  
  def __init__(self, name, resources, artifact=None, is_royal=False
               slot=None, machine=None, family=None):
    '''Init Recipe'''
    self.name = assert_type(name, 'name', str)
    self.artifact = assert_type(artifact, 'artifact', str)
    self.is_royal = assert_type(is_royal, 'is_royal', bool)
    self.resources = assert_type(resources, 'resources', dict)
    self.slot = assert_type(slot, 'slot', str)
    self.machine = assert_type(machine, 'machine', str)
    self.family = assert_type(family, 'family', str)

  def compute_masteries(self, masteries):

  def cost_price(self, tier, ench, resources, *, 
                 tax=0, retrate=0, artifacts=None, journals=None)
    '''Calculate cost price'''
    # Arguments validation
    tier, ench = assert_tier_ench(tier, ench)
    resources = assert_type(resources, 'resources', CSVTable, convert=False)

    err_no_data = f'Not enought data to compute \'{self.name} {tier}.{ench}\'')

    # Cost price calculation
    result = np.float64(0.0)
    res_prices = resources.get_row(f'{tier}.{ench}')
    for name, amount in self.resources.items():
      cost = res_prices.get(name, None)
      if cost is not None:
        result += float(cost) * float(amount)
      else:
        print(err_no_data)
        return np.NAN

    # Taking resource return rate into account
    # TODO Find smarter way to find retrate
    result *= 1 - retrate

    # Add Artifacts and Royals
    if self.artifact is not None:
      artifacts = assert_type(artifacts, 'artifacts', CSVTable, convert=False)
      art_prices = artifacts.get_row('{tier}')
      art_cost = art_prices.get(self.artifact, np.NAN)

      if art_cost == np.NAN: 
        print(err_no_data)
        return np.NAN

      art_amount = 1
      if self.is_royal:
        art_amount = g_const['royal'][self.slot][tier-g_const['min_tier']]

      result += art_amount * art_cost

    '''
    if journals is not None:
      if self.machine == 'None':
        die(f'Can\'t calculate journals for \'{self.name}\': mahing required')
      journals = assert_type(journals, 'journals', CSVTable, convert=False)
      journal_prices = artifacts.get_row('{tier}')
      journal_price = journal_prices.get(self.machine, np.NAN)
      if journal_price == np.NAN:
        print(err_no_data)
        return np.NAN
      journal_fame = g_const['fame_per_journal'][tier-4]
      result -= self.fame(tier, ench) / journal_fame * journal_price
    '''

    # Taking into account taxes
    result += g_const['item_value2food'] * 
              self.item_value(tier, ench) / 100 * tax
  
    return result

  # Global table with artifact item values
  # Located in config/, it means that should be configured just once
  artifact_item_values = CSVTable()
  artifact_item_values.read('config/artifact_item_values.csv')

  def item_value(self, tier, ench):
    '''Calculate item value'''
    # Arguments validation
    tier, ench = assert_tier_ecnh(tier, ench)

    resource_item_value = g_const['res_item_value_base'] * 
                          g_const['res_item_value_coeff'] ** (tier + ench)
    
    # Resources item value
    result = sum(self.resources.items()) * resource_item_value  

    # Artifact and Royal item value
    if self.artifact != 'None':
      art_item_values = artifact_item_values.get_row(f'item_value')
      base_item_value = art_item_values.get(self.artifact, None)
      if base_item_value is None:
        die(f'Can\'t get item value of \'{self.artifact}\' from config')
      idx = tier - g_const['min_tier']
      factor = g_const['art_item_value_coeff'] ** idx
      art_item_value = base_item_value * factor
      art_amount = 1
      if self.is_royal:
        if self.slot == 'None':
          die(f'Can\'t compute iteam value of \'{self.name} {tier}.{ench}\': slot is required')
        art_amount = g_const['royal'][self.slot][idx]
      result += art_amount * art_item_value

    return result

  def fame(self, tier, ench, premium=False):
    '''Calculate fame'''
    tier, ench = assert_tier_ench(tier, ench)
    idx = tier - g_const['min_tier']
    base_fame = g_const['base_fame_coeffs'][idx] * sum(self.resources.items())
    result = base_fame

    if not self.is_royal:
      result += ench * (base_fame - 7.5 * tier)
      if self.artifact != 'None':
        result += 500
    else:
      result += tier * g_const['royal_fame_coeffs'][idx]

    if premium:
      result *= 1.5

    return result

  # Global table with base focus cost
  # Located in config/, it means that should be configured just once
  base_focus_cost = CSVTable()
  base_focus_cost.read('config/base_focus_cost.csv')

  def focus_cost(self, tier, ench, masteries=None):
    '''Calculate focus cost'''
    # TODO Should be computed with base_focus_cost table
    # TODO Should be computed with masteries
    tier, ench = assert_tier_ench(tier, ench)
    masteries = assert_type
    if self.slot == 'None':
      die(f'Can\'t compute focus cost for \'{self.name} {tier}.{ench}\': slot is required')
    base_costs_list = base_focus_cost.get_row(f'{tier}.{ench}')
    base_cost = base_costs_list.get(self.slot, None)
    if base_cost is None:
      die(f'Can\'t get base focus cost for \'{self.slot} {tier}.{ench}\' from config')
    if self.family == 'None':
      die(f'Can\'t compute focus cost for \'{self.name} {tier}.{ench}\': family is required')
    family_masteries = masteries.get(self.family, None)
    if family_masteries is None:
      print('Can\'t compute focus cost for \'{self.name} {tier}.{ench}\': family masteries is required')

    self.focus_efficienty = 0
    self.quality = 0
    base_eff = g_const['base_mastery_eff']
    base_qual = g_const['base_mastery_qual']
    main_eff = g_const['main_mastery_eff']
    main_qual = g_const['main_mastery_qual']
    for name, mastery in masteries.values():
      if name == self.name:
        self.focus_efficienty += (base_eff + main_eff) * mastery
        self.quality += (base_quak + main_qual) * mastery
      else:
        self.focus_efficienty += base_eff * mastery
        self.quality += base_qual * mastery
       
  def focus_cost(self, 
    denominator = (g_const['focus_cost_coeff'] ** g_const['focus_cost_divider'])
    cost = self.focus_efficiency / denominator

    return cost
    
  def quality(self, tier, ench, masteries=None)
    # TODO Haven't found info about it yet
    raise NotImplementedError()

def main():
  resources = CSVTable()
  resources.read('resources.csv')
  item_values = CSVTable()
  item_values.read('item_values.csv')
  config = yaml_load('config.yaml')
  recipes = yaml_load('recipes.yaml')

  print(config)
  tax = config['tax']
  retrate = config['retrate']

  levels = resources.rows()
  costprices = CSVTable(rows=levels)

  for name, recipe_dict in recipes.items():
    prices = {}
    recipe = Recipe.from_dict(recipe_dict)
    it_val = item_values.get_column(name)
    for tier in levels:
      res = resources.get_row(tier)
      try:
        price = recipe.cost_price(tax=it_val.get(tier, 0.0), retrate=retrate, **res)
      except ValueError:
        price = np.NAN
        print(f'Can\'t compute price for \'{name} {tier}\'')
      prices[tier] = price
    costprices.add_column(name, prices)

  costprices.write('prices.csv')
      
if __name__ == '__main__':
  main()
