
# coding: utf-8

# In[52]:

import pandas as pd
import optics as opt
import json, re, smopy, math, sys, googlemaps
from matplotlib import pyplot as plt


# In[18]:

#%matplotlib inline


# In[19]:

zipcode = int(sys.argv[1])


# In[20]:

print "loading evictions..."
evictions = pd.read_csv('merged_1990.csv',usecols=['year','zip','id','lat','lon'])
print "loaded " + str(len(evictions)) + "records"


# In[21]:

evictions = evictions.loc[evictions['year'] > 2011].loc[evictions['zip'] == zipcode][['id','lat','lon',]]


# In[22]:

points = [opt.Point(row['lat'],row['lon'],row['id']) for i,row in evictions.iterrows()]


# In[34]:

print "clustering evictions..."
optics = opt.Optics(points, 100, 7) # 100m radius for neighbor consideration, cluster size >= 2 points
optics.run()                    # run the algorithm
clusters = optics.cluster(65)
print "Number of clusters: " + str(len(clusters))


# In[35]:

#narrow to clusters >150m
for cluster in clusters:
    radius = cluster.region()[1]
    if radius > 150:
        clusters.remove(cluster)
print "Number of smol clusters: " + str(len(clusters))


# In[36]:

#could a voter be in multiple clusters? clusters can't overlap right?
#SIDE FX AW YEAH
def inCluster(voter):
    p = opt.Point(voter['lat'],voter['lng'],voter['ID'])
    for cluster in clusters:
        center = cluster.centroid()
        radius = cluster.region()[1]
        if p.distance(center) <= radius:
            cluster.voters.append(voter['ID'])
            return True


# In[61]:

col_names = ['first_name','last_name','gender','location','apartment_number','owner_1','owner_2','council_district']
cols_4_analysis = ['ID','lat','lng'] + col_names


# In[62]:

#load in voter data
print "loading voters..."
voter_file = "voters_geocoded_" + str(zipcode) + ".csv"
voters = pd.read_csv(voter_file,encoding='utf-8',usecols=cols_4_analysis)
print "loaded " + str(len(voters)) + " records"
voters_short = voters[['ID','lat','lng']]
for cluster in clusters:
    cluster.voters = []
print "locating voters in clusters..."
for i,row in voters_short.iterrows():
    inCluster(row)


# In[39]:

#compute density
print "calculating density..."
for cluster in clusters:
    area = math.pi * (cluster.region()[1] ** 2)
    eviction_density = len(cluster.points) / area #number of evictions over area of cluster
    voter_density = len(cluster.voters) / area
    cluster.density = eviction_density * voter_density
clusters_by_density = sorted(filter(lambda c: len(c.voters) > 0 , clusters), key=lambda cluster: cluster.density, reverse=True)


# In[63]:

#print "voters\tevictions\tcenter"
#for c in clusters_by_density:
   #print "%s\t%s\t%s" % (len(c.voters),len(c.points),c.centroid())


# In[46]:

print "getting bounding box..."
gmaps = googlemaps.Client(key='AIzaSyBbv3SgWdKhgZWNhHVy8QXfYFCSONWj2Jk')
bounds = gmaps.geocode(zipcode)[0]['geometry']['bounds']
lat = [bounds['southwest']['lat'],bounds['northeast']['lat']]
lon = [bounds['southwest']['lng'],bounds['northeast']['lng']]
fig= plt.figure(figsize=(13,13))
ax = fig.add_axes([0.0,0.0,1.0,1.0])

print "initializing map..."
smomap = smopy.Map((lat[0],lon[0],lat[1],lon[1]),z=15)
mapthing = smomap.show_mpl(figsize=(13,13),ax = ax)

##get a pixel per meter ratio:
p1 = clusters[0].points[0]
p2 = clusters[0].points[1]
pxpts = [smomap.to_pixels(p1.latitude,p1.longitude), smomap.to_pixels(p2.latitude,p2.longitude)]

hdist = p1.distance(p2)
pxdist = (((pxpts[0][0] - pxpts[1][0]) ** 2) + ((pxpts[0][1] - pxpts[1][1]) ** 2)) ** 0.5
ppm = pxdist/(hdist)

print "drawing evictions..."
for point in points:
    if point.latitude > lat[0] and point.latitude < lat[1] and point.longitude < lon[1]:
        x,y = smomap.to_pixels(point.latitude,point.longitude)
        mapthing.scatter(x,y,alpha=1,s=3,color='green');

print "drawing voters..."
for i,voter in voters_short.iterrows():
    if voter['lat'] > lat[0] and voter['lat'] < lat[1] and voter['lng'] < lon[1]:
        x,y = smomap.to_pixels(voter['lat'],voter['lng'])
        mapthing.scatter(x,y,alpha=.5,s=1,color='red');

print "drawing clusters..."
for cluster in clusters_by_density[0:20]:
    radius = cluster.region()[1]
    x,y = smomap.to_pixels(cluster.centroid().latitude,cluster.centroid().longitude)
    circ = plt.Circle((x,y),ppm*radius,facecolor='blue',edgecolor='black', alpha = 0.2)
    fig.gca().add_artist(circ)

plt.savefig('voters_evictions_clustered_' + str(zipcode) + '.pdf')


# In[487]:

#print clusters
#for i, cluster in enumerate(clusters_by_density[0:20]):
    #print i, len(cluster.points), len(cluster.voters), cluster.centroid()


# In[49]:

col_names.insert(0,'priority')
all_top_voters = pd.DataFrame(columns=col_names)
print "creating list of voters by cluster density..."
for i, cluster in enumerate(clusters_by_density[0:20]):
    top_voters = voters.loc[voters['ID'].isin(cluster.voters)][col_names[1:]]
    #top_voters = top_voters.loc[top_voters['owner_1'].str.contains(top_voters['last_name'])]
    top_voters = top_voters.sort_values('location')
    top_voters['priority'] = i
    all_top_voters = pd.concat([all_top_voters,top_voters])

all_top_voters = all_top_voters[col_names]


# In[50]:

#print top group
print "saving list to file..."
all_top_voters.to_excel('voters' + str(zipcode)+'.xlsx')
all_top_voters.loc[all_top_voters['priority'] == 1]


# In[ ]:



