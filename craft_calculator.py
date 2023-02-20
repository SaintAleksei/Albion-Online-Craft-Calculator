#!/usr/bin/python3

from csvtable import CSVTable
import yaml
import numpy as np
import argparse

# TODO Tests
# TODO Unix-like interface
# TODO Doc-strings

# Global constants, gathered dierctly from game
g_const =\
{
  # Tiers
  'min_tier': 4,
  'max_tier': 8,
  # Enchantments
  'min_ench': 0,
  'max_ench': 3,
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
  'fame_per_journal': [3600, 7200, 14400, 28380, 58590],
  # List of supported slots
  'slots': ['head', 'body', 'legs', 'right-hand', 'left-hand', 'two-handed'],
  # Coeff to compute artifact item values 
  'artifact_item_value_coeff': 2,
}


# Helpfull functions, maybe will be restructed in future
def assert_tier_ench(tier, ench):
  tier = int(tier)
  ench = int(ench)
  if not g_const['min_tier']  <= tier <= g_const['max_tier']:
    raise ValueError('Bad tier')
  if not g_const['min_ench'] <= ench <= g_const['max_tier']:
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
  else:
    return obj

def yaml_load(fname):
  data = None
  with open(fname) as f:
    data = yaml.full_load(f)
  return data

def die(message):
  raise RuntimeError(message)

def run_test_case(name, args_generator, func, comparator):
  print(f'Running test \'{name}\'...', end=' ')
  args, kwargs = args_generator()
  result = func(*args, **kwargs)
  if comparator(result):
    print(f'[SUCCESS]')
  else:
    print(f'[FAILURE]')

def run_tests(tests):
  for name, args in tests:
    run_test_case(name, *args)

# Main class for armor, weapons and off-hands crafting calculations
# TODO Should be generalized to ALL game items
class Recipe:
  '''Item craft recipe'''

  # Global table with base focus cost
  # Located in config/, it means that should be configured just once
  base_focus_cost = CSVTable()
  base_focus_cost.read('config/base_focus_cost.csv')
  # Global table with artifact item values
  # Located in config/, it means that should be configured just once
  artifact_item_values = CSVTable()
  artifact_item_values.read('config/artifact_item_values.csv')

  @classmethod
  def configure(cls, *, base_focus_cost, artifact_item_values_fname):
    if base_focus_cost is not None:
      cls.base_focus_cost = base_focus_cost
    if artifact_item_values is not None:
      cls.artifact_item_values = artifact_item_values
  
  def __init__(self, name, resources, *, artifact, is_royal,
               slot, machine, family):
    '''Init Recipe'''
    self.name = assert_type(name, 'name', str)
    self.artifact = assert_type(artifact, 'artifact', str)
    self.is_royal = assert_type(is_royal, 'is_royal', bool)
    self.resources = assert_type(resources, 'resources', dict)
    self.slot = assert_type(slot, 'slot', str)
    self.machine = assert_type(machine, 'machine', str)
    self.family = assert_type(family, 'family', str)

  def cost_price(self, tier, ench, resources, *, 
                 tax=0, retrate=0, artifacts=None, journals=None):
    '''Calculate cost price'''
    # Arguments validation
    tier, ench = assert_tier_ench(tier, ench)
    resources = assert_type(resources, 'resources', CSVTable, convert=False)

    err_no_data = f'Not enought data to compute \'{self.name} {tier}.{ench}\''

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
    if self.artifact != 'None':
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
    result += g_const['item_value2food'] * self.item_value(tier, ench) / 100 * tax

    return result

  def item_value(self, tier, ench):
    '''Calculate item value'''
    # Arguments validation
    tier, ench = assert_tier_ench(tier, ench)

    resource_item_value = g_const['res_item_value_base'] * g_const['res_item_value_coeff'] ** (tier + ench - 1)
    # FIXME Shoud be done inside CSVTable
    resource_item_value = assert_type(resource_item_value, 'resource_item_value', float)

    # Resources item value
    result = sum(self.resources.values()) * resource_item_value  

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
        art_amount = g_const['royal'][self.slot][idx]
      result += art_amount * art_item_value

    return result

  def fame(self, tier, ench):
    '''Calculate fame'''
    tier, ench = assert_tier_ench(tier, ench)
    idx = tier - g_const['min_tier']
    base_fame = g_const['base_fame_coeffs'][idx] * sum(self.resources.values())
    result = base_fame * g_const['fame_factor'] ** ench

    return result

  @staticmethod
  def compute_masteries(name, family, masteries):
    # TODO
    '''
    family_masteries = masteries.get(family, None)
    if family_masteries is None:
      print('Can\'t compute masteries for \'{self.name} {tier}.{ench}\': family masteries is required')
      return

    focus_efficienty = 0
    quality = 0
    for name, coeffs in family_masteries.values():
      if name == self.name:
        focus_efficienty += (coeffs[1] + coeffs[2]) * coeffs[0]
        quality += (coeffs[3] + coeffs[4]) * coeffs[0]
      else:
        focus_efficienty += coeffs[1] * coeffs[0]
        quality += coeffs[1] * coeffs[0]

    return focus_efficienty, quality
    '''
    raise NotImplementedError
       
  def focus_cost(self, tier, ench, focus_efficiency):
    tier, ench = assert_tier_ench(tier, ench)
    base_costs_list = base_focus_cost.get_row(f'{tier}.{ench}')
    base_cost = base_costs_list.get(self.slot, None)
    if base_cost is None:
      die(f'Can\'t get base focus cost for \'{self.slot} {tier}.{ench}\' from config')

    power = focus_efficienty / g_const['focus_cost_divider']
    denominator = g_const['focus_cost_coeff'] ** power
    cost = base_cost / denominator

    return cost

  def quality(self, tier, ench, masteries=None):
    # TODO Haven't found info about it yet
    # Here should be some code, that converts self.quality to chances
    raise NotImplementedError

  @staticmethod
  def tests():
    print('Running tests...')
    resources = CSVTable()
    resources.read('tests/test_resources.csv')
    test = CSVTable()
    test.read('tests/test_results.csv')
    test_params = yaml_load('tests/test_params.yaml')
    recipe_dict = yaml_load('tests/test_recipe.yaml')
    recipe = Recipe(**recipe_dict)

    for row in test.rows():
      tier, ench = row.split('.')
      cost_price = int(recipe.cost_price(tier, ench, resources, **test_params))
      fame = int(recipe.fame(tier, ench))
      item_value = int(recipe.item_value(tier, ench))
      true_results = test.get_row(row)
      if int(true_results['fame']) - fame > 1 or\
         int(true_results['item_value']) - item_value > 1 or\
         int(true_results['cost_price']) - cost_price > 1:
        print(f'Test failed at \'{row}\'')
        print(f'\tcost_price = {cost_price} (expected {true_results["cost_price"]})')
        print(f'\tfame       = {fame} (expected {true_results["fame"]})')
        print(f'\titem_value = {item_value} (expected {true_results["item_value"]})')
        return False

    print('All tests succeed!!!')
    return True
      
    
def main():
  Recipe.tests()
      
if __name__ == '__main__':
  main()
