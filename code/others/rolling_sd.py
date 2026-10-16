import pandas as pd
import matplotlib.pyplot as plt 
import matplotlib.dates as mdates
import seaborn as sb 
data = pd.read_csv(r"E:\Users\BROTHER COMPUTER\Desktop\research\Cleaned_Data\master_clean.csv")


data["rolling_sd"] = (
    data.groupby('commodity')['Average_price']
    .rolling(window = 12)
    .std()
    .reset_index(level = 0, drop = True)
)
print("Done")
data['Date'] = pd.to_datetime(data['Date'])
plt.figure(figsize = (12,12))
sb.lineplot(data = data,x = 'Date', y = 'rolling_sd', hue = 'commodity')
plt.axvline(x=pd.to_datetime('2022-02-01'), color = 'red', linestyle = "--", label = 'Start of Ukraine-Russia War')
plt.axvline(x=pd.to_datetime('2024-04-01'), color = 'black', linestyle = "--", label = 'Start of Iran-Isarel War')
plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval = 2))
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y - %m'))
plt.xticks(rotation = 45 ,ha= 'right', fontsize = 8 ) 
plt.tight_layout()
plt.legend()
plt.show()
commodities = data['commodity'].unique()

fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(15, 8), sharex=True)
axes = axes.flatten()

colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

for i, comm in enumerate(commodities):
    ax = axes[i]
    subset = data[data['commodity'] == comm]
    
    ax.plot(subset['Date'], subset['rolling_sd'], color=colors[i], linewidth=1.5, label=comm)
    ax.axvline(x=pd.to_datetime('2022-02-01'), color='red', linestyle='--', alpha=0.7, label='Ukraine War')
    ax.axvline(x=pd.to_datetime('2024-04-01'), color='black', linestyle='--', alpha=0.7, label='Iran-Israel War')
    
    ax.set_title(f'Rolling SD: {comm}', fontsize=10, fontweight='bold')
    ax.set_ylabel('Rolling SD', fontsize=9)
    
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', fontsize=5)
    ax.legend(fontsize=7, loc='upper left')

plt.tight_layout()
plt.show()
