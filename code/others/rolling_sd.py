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