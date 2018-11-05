# Pulls all the other functions together to make magic!
# Author: Christopher Arderne
# Date: 26 November 2016
# Python version: 3.5

# Updated June 2018 by Andreas Sahlberg (KTH dESA)
# Modified grid algorithm and population calibration to improve computational speed

import os
from onsset import *
import tkinter as tk
from tkinter import filedialog, messagebox

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)

messagebox.showinfo('OnSSET', 'Open the specs file')
specs_path = filedialog.askopenfilename()

specs = pd.read_excel(specs_path, index_col=0)

coordinate_units = 1000  # 1000 if coordinates are in m, 1 if coordinates are in km

# specs_directory = str(input('Enter the directory of the specs file: '))
# os.chdir(specs_directory)
# specs_path = str(input('Enter the name of the specs file: '))
#
# try:
#     specs = pd.read_excel(specs_path, index_col=0)
# except FileNotFoundError:
#     specs = pd.read_excel(str(specs_path + '.xlsx'), index_col=0)

countries = ['Benin']
# countries = str(input('countries: ')).split()
# countries = specs.index.tolist() if 'all' in countries else countries

choice = 2
# choice = int(input('1 to calibrate and prep, 2 to run a scenario: '))

if choice == 0:
    messagebox.showinfo('OnSSET', 'Open the csv file with GIS data')
    settlements_csv = filedialog.askopenfilename()
    messagebox.showinfo('OnSSET', 'Select the folder to save split countries')
    base_dir = filedialog.asksaveasfilename()

    print('\n --- Splitting --- \n')

    df = pd.read_csv(settlements_csv)

    for country in countries:
        print(country)
        df.loc[df[SET_COUNTRY] == country].to_csv(base_dir + '.csv', index=False)

elif choice == 1:
    messagebox.showinfo('OnSSET', 'Open the csv file containing the extracted GIS data')
    base_dir = filedialog.askopenfilename()
    messagebox.showinfo('OnSSET', 'Browse to result folder and name the calibrated file')
    output_dir = filedialog.asksaveasfilename()

    print('\n --- Prepping --- \n')

    for country in countries:
        print(country)
        settlements_in_csv = base_dir  # os.path.join(base_dir, '{}.csv'.format(country))
        settlements_out_csv = output_dir + '.csv'  # os.path.join(output_dir, '{}.csv'.format(country))

        onsseter = SettlementProcessor(settlements_in_csv)

        onsseter.condition_df()
        onsseter.grid_penalties()
        onsseter.calc_wind_cfs()

        pop_actual = specs.loc[country, SPE_POP]
        pop_future = specs.loc[country, SPE_POP_FUTURE]
        urban_current = specs.loc[country, SPE_URBAN]
        urban_future = specs.loc[country, SPE_URBAN_FUTURE]
        urban_cutoff = specs.loc[country, SPE_URBAN_CUTOFF]

        elec_actual = specs.loc[country, SPE_ELEC]
        pop_cutoff = specs.loc[country, SPE_POP_CUTOFF1]
        min_night_lights = specs.loc[country, SPE_MIN_NIGHT_LIGHTS]
        max_grid_dist = specs.loc[country, SPE_MAX_GRID_DIST]
        max_road_dist = specs.loc[country, SPE_MAX_ROAD_DIST]
        pop_tot = specs.loc[country, SPE_POP]
        pop_cutoff2 = specs.loc[country, SPE_POP_CUTOFF2]

        urban_cutoff, urban_modelled = onsseter.calibrate_pop_and_urban(pop_actual, pop_future, urban_current,
                                                                        urban_future, urban_cutoff)
        min_night_lights, max_grid_dist, max_road_dist, elec_modelled, pop_cutoff, pop_cutoff2, urban_elec_ratio, rural_elec_ratio = \
            onsseter.elec_current_and_future(elec_actual, pop_cutoff, min_night_lights,
                                             max_grid_dist, max_road_dist, pop_tot, pop_cutoff2)

        print(urban_elec_ratio)
        print(rural_elec_ratio)

        specs.loc[country, SPE_MIN_NIGHT_LIGHTS] = min_night_lights
        specs.loc[country, SPE_MAX_GRID_DIST] = max_grid_dist
        specs.loc[country, SPE_MAX_ROAD_DIST] = max_road_dist
        specs.loc[country, SPE_ELEC_MODELLED] = elec_modelled
        specs.loc[country, SPE_POP_CUTOFF1] = pop_cutoff
        specs.loc[country, SPE_POP_CUTOFF2] = pop_cutoff2
        specs.loc[country, SPE_URBAN_MODELLED] = urban_modelled
        specs.loc[country, SPE_URBAN_CUTOFF] = urban_cutoff

        try:
            specs.to_excel(specs_path)
        except ValueError:
            specs.to_excel(specs_path + '.xlsx')

        onsseter.df.to_csv(settlements_out_csv, index=False)

elif choice == 2:
    wb_tiers_all = {1: 8, 2: 44, 3: 160, 4: 423, 5: 598}
    print("""\nWorld Bank Tiers of Electricity Access
          1: {} kWh/person/year
          2: {} kWh/person/year
          3: {} kWh/person/year
          4: {} kWh/person/year
          5: {} kWh/person/year""".format(wb_tiers_all[1], wb_tiers_all[2], wb_tiers_all[3],
                                          wb_tiers_all[4], wb_tiers_all[5]))
    wb_tier_urban = int(input('Enter the tier number for urban: '))
    wb_tier_peri_urban = int(input('Enter the tier number for peri-urban: '))
    wb_tier_rural = int(input('Enter the tier number for rural: '))

    # diesel_high = True if 'y' in input('Use high diesel value? <y/n> ') else False
    diesel_high = True
    diesel_tag = 'high' if diesel_high else 'low'

    messagebox.showinfo('OnSSET', 'Open the csv file with calibrated GIS data')
    base_dir = filedialog.askopenfilename()
    messagebox.showinfo('OnSSET', 'Browse to result folder and name the scenario to save outputs')
    output_dir = filedialog.asksaveasfilename()

    # Uncomment row below if running multiple countries/regions
    do_combine = False
    # do_combine = True if 'y' in input('Combine countries into a single file? <y/n> ') else False

    print('\n --- Running scenario --- \n')

    for country in countries:
        # create country_specs here
        print(' --- {} --- {} --- {} --- '.format(country, wb_tier_urban, diesel_tag))
        settlements_in_csv = base_dir
        settlements_out_csv = output_dir + '.csv'
        summary_csv = output_dir + 'summary.csv'

        onsseter = SettlementProcessor(settlements_in_csv)

        diesel_price = specs[SPE_DIESEL_PRICE_HIGH][country] if diesel_high else specs[SPE_DIESEL_PRICE_LOW][country]
        grid_price = specs[SPE_GRID_PRICE][country]
        existing_grid_cost_ratio = specs[SPE_EXISTING_GRID_COST_RATIO][country]
        num_people_per_hh_rural = float(specs[SPE_NUM_PEOPLE_PER_HH_RURAL][country])
        num_people_per_hh_urban = float(specs[SPE_NUM_PEOPLE_PER_HH_URBAN][country])
        max_grid_extension_dist = float(specs[SPE_MAX_GRID_EXTENSION_DIST][country])
        energy_per_hh_rural = wb_tiers_all[wb_tier_rural] * num_people_per_hh_rural
        energy_per_hh_periurban = wb_tiers_all[wb_tier_peri_urban] * num_people_per_hh_rural
        energy_per_hh_urban = wb_tiers_all[wb_tier_urban] * num_people_per_hh_urban

        Technology.set_default_values(start_year=2016,
                                      end_year=2030,
                                      discount_rate=0.0425,
                                      grid_cell_area=1,
                                      mv_line_cost=9000,
                                      lv_line_cost=5000,
                                      mv_line_capacity=50,
                                      lv_line_capacity=10,
                                      lv_line_max_length=30,
                                      hv_line_cost=53000,
                                      mv_line_max_length=50,
                                      hv_lv_transformer_cost=5000,
                                      mv_increase_rate=0.1)

        onsseter.calc_education_demand(wb_tier_urban, wb_tier_rural, wb_tier_peri_urban)
        onsseter.calc_health_demand(wb_tier_urban, wb_tier_rural, wb_tier_peri_urban)
        onsseter.new_connections_prod(energy_per_hh_rural, energy_per_hh_urban, energy_per_hh_periurban, num_people_per_hh_rural, num_people_per_hh_urban)

        grid_calc = Technology(om_of_td_lines=0.1,
                               distribution_losses=float(specs[SPE_GRID_LOSSES][country]),
                               connection_cost_per_hh=150,
                               base_to_peak_load_ratio=float(specs[SPE_BASE_TO_PEAK][country]),
                               capacity_factor=1,
                               tech_life=30,
                               grid_capacity_investment=float(specs[SPE_GRID_CAPACITY_INVESTMENT][country]),
                               grid_price=grid_price)

        mg_hydro_calc = Technology(om_of_td_lines=0.03,
                                   distribution_losses=0.05,
                                   connection_cost_per_hh=100,
                                   base_to_peak_load_ratio=0.9,
                                   capacity_factor=0.5,
                                   tech_life=30,
                                   capital_cost={1: 10556, 100: 5000, 5000: 2457},
                                   om_costs=0.02,
                                   mg_hydro=True)

        mg_wind_calc = Technology(om_of_td_lines=0.03,
                                  distribution_losses=0.05,
                                  connection_cost_per_hh=100,
                                  base_to_peak_load_ratio=0.9,
                                  capital_cost={100: 3000, 1000: 2889, 10000: 1773},
                                  om_costs=0.02,
                                  tech_life=20,
                                  mg_wind=True)

        mg_pv_calc = Technology(om_of_td_lines=0.03,
                                distribution_losses=0.05,
                                connection_cost_per_hh=100,
                                base_to_peak_load_ratio=0.9,
                                tech_life=20,
                                om_costs=0.02,
                                capital_cost={50: 14827, 75: 9498, 100: 5280, 200: 3081},
                                # capital_cost={50: 12076, 75: 7735, 100: 4300, 200: 2510},
                                mg_pv=True)

        sa_pv_calc = Technology(base_to_peak_load_ratio=0.9,
                                tech_life=15,
                                om_costs=0.02,
                                capital_cost={0.020: 5000, 0.050: 3400, 0.100: 8000, 0.200: 4580, 0.300: 3330},
                                # capital_cost={0.020: 20000, 0.050: 11050, 0.100: 7660, 0.200: 5780, 0.300: 5070},
                                # capital_cost={0.020: 0.7*5000, 0.050:  0.7*3400, 0.100:  0.7*8000, 0.200:  0.7*4580, 0.300:  0.7*3330},
                                standalone=True)

        mg_diesel_calc = Technology(om_of_td_lines=0.03,
                                    distribution_losses=0.05,
                                    connection_cost_per_hh=100,
                                    base_to_peak_load_ratio=0.9,
                                    capacity_factor=0.7,
                                    tech_life=15,
                                    om_costs=0.1,
                                    efficiency=0.33,
                                    capital_cost={100: 721, 1000: 674, 5000: 467, 25000: 392},
                                    diesel_price=diesel_price,
                                    diesel_truck_consumption=33.7,
                                    diesel_truck_volume=15000,
                                    mg_diesel=True)

        sa_diesel_calc = Technology(base_to_peak_load_ratio=0.9,
                                    capacity_factor=0.7,
                                    tech_life=10,
                                    om_costs=0.1,
                                    capital_cost={0.020: 938, 0.050: 938, 0.100: 938, 0.200: 938, 0.300: 938},
                                    diesel_price=diesel_price,
                                    standalone=True,
                                    efficiency=0.28,
                                    diesel_truck_consumption=14,
                                    diesel_truck_volume=300)

        pv_diesel_hyb = Technology(om_of_td_lines=0.03,
                                   distribution_losses=0.05,
                                   connection_cost_per_hh=100,
                                   base_to_peak_load_ratio=0.5,
                                   tech_life=15,
                                   diesel_price=diesel_price,
                                   diesel_truck_consumption=33.7,
                                   diesel_truck_volume=15000)


        onsseter.set_scenario_variables(energy_per_hh_rural, energy_per_hh_urban, energy_per_hh_periurban,
                                        num_people_per_hh_rural, num_people_per_hh_urban)

        print('Preparing urban mg pv-diesel hybrid reference table')
        urban_hybrid = pv_diesel_hyb.pv_diesel_hybrid(energy_per_hh_urban, max(onsseter.df[SET_GHI]),
                                                      max(onsseter.df[SET_TRAVEL_HOURS]))

        print('Preparing rural mg pv-diesel hybrid reference table')
        rural_hybrid = pv_diesel_hyb.pv_diesel_hybrid(energy_per_hh_rural, max(onsseter.df[SET_GHI]),
                                                      max(onsseter.df[SET_TRAVEL_HOURS]))

        onsseter.calculate_off_grid_lcoes(mg_hydro_calc, mg_wind_calc, mg_pv_calc,
                                          sa_pv_calc, mg_diesel_calc, sa_diesel_calc,
                                          pv_diesel_hyb, urban_hybrid, rural_hybrid)

        grid_lcoes_rural = grid_calc.get_grid_table(energy_per_hh_rural, num_people_per_hh_rural,
                                                    max_grid_extension_dist)
        grid_lcoes_urban = grid_calc.get_grid_table(energy_per_hh_urban, num_people_per_hh_urban,
                                                    max_grid_extension_dist)
        grid_lcoes_periurban = grid_lcoes_rural
        # grid_lcoes_periurban = grid_calc.get_grid_table(energy_per_hh_periurban, num_people_per_hh_rural,
        #                                             max_grid_extension_dist)
        onsseter.run_elec(grid_lcoes_rural, grid_lcoes_urban, grid_lcoes_periurban, grid_price,
                          existing_grid_cost_ratio, max_grid_extension_dist, coordinate_units, grid_calc)

        onsseter.results_columns(mg_hydro_calc, mg_wind_calc, mg_pv_calc, sa_pv_calc,
                                 mg_diesel_calc, sa_diesel_calc, grid_calc, pv_diesel_hyb, urban_hybrid, rural_hybrid)

        summary = onsseter.calc_summaries()
        summary.name = country

        try:
            summary.to_csv(summary_csv, header=True)
        except PermissionError:
            if 'y' in input('Summary file open. Close it and enter "y" to overwrite (or rename the open file first)'):
                summary.to_csv(summary_csv, header=True)
            else:
                pass
        try:
            onsseter.df.to_csv(settlements_out_csv, index=False)
        except PermissionError:
            if 'y' in input('Output csv file open. Close it and enter "y" to overwrite (or rename open file first)'):
                onsseter.df.to_csv(settlements_out_csv, index=False)
            else:
                pass

    if do_combine:
        print('\n --- Combining --- \n')
        df_base = pd.DataFrame()
        summaries = pd.DataFrame(columns=countries)

        for country in countries:
            print(country)
            df_add = pd.read_csv(os.path.join(output_dir, '{}_{}_{}.csv'.format(country, wb_tier_urban, diesel_tag)))
            df_base = df_base.append(df_add, ignore_index=True)

            summaries[country] = pd.read_csv(os.path.join(output_dir, '{}_{}_{}_summary.csv'.format(country,
                                                                                                    wb_tier_urban,
                                                                                                    diesel_tag)),
                                             squeeze=True, index_col=0)

        print('saving csv')
        df_base.to_csv(os.path.join(output_dir, '{}_{}_{}.csv'.format(wb_tier_urban,
                                                                      wb_tier_rural, diesel_tag)), index=False)
        summaries.to_csv(os.path.join(output_dir, '{}_{}_{}_summary.csv'.format(wb_tier_urban,
                                                                                wb_tier_rural, diesel_tag)))

    logging.info('Scenario run finished')