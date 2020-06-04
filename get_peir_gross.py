import os
import requests
import csv
import json
from bs4 import BeautifulSoup
from PIL import Image
requests.adapters.DEFAULT_RETRIES = 5
s = requests.session()
s.keep_alive = False

# set continue_extract = True if an interruption occurs during your download
continue_extract = False

def create_csv():
	path = "page_extracted.csv"
	with open(path, 'w', newline='') as f:
		csv_write = csv.writer(f)
		csv_head = ["one_level_directory", 'two_level_directory']
		csv_write.writerow(csv_head)


def write_csv(data_row):
	path = "page_extracted.csv"
	with open(path, 'a+', newline='') as f:
		csv_write = csv.writer(f)
		csv_write.writerow(data_row)


def read_csv():
	path = "page_extracted.csv"
	one_class_pages, two_class_pages = [], []
	with open(path, "r") as f:
		csv_read = csv.reader(f)
		for line in csv_read:
			# print(line)
			if line[0]:
				one_class_pages.append(line[0])
			if line[1]:
				two_class_pages.append(line[1])
		return one_class_pages, two_class_pages


def split_images(images, keys, filename):
	new_images = {}

	for key in keys:
		new_images[key] = images[key]

	with open(filename, "w") as output_file:
		for new_image in new_images:
			output_file.write(new_image + "\t" + new_images[new_image])
			output_file.write("\n")


# JSON saving
def save_captions(image_captions, image_tags):
	with open("peir_gross/peir_gross_captions.json", "w") as output_file:
		output_file.write(json.dumps(image_captions))
	with open("peir_gross/peir_gross_tags.json", "w") as output_file:
		output_file.write(json.dumps(image_tags))


# create dataset and images folder
if not os.path.isdir("peir_gross/peir_gross_images/"):
	os.makedirs("peir_gross/peir_gross_images/")

image_existed = os.listdir("peir_gross/peir_gross_images/")
# the main page of the pathology category that contains the collections of all the sub-categories
base_url = "http://peir.path.uab.edu/library"
main_page_url = "http://peir.path.uab.edu/library/index.php?/category/2"  # PEIR pathology
main_page = s.get(main_page_url)
soup = BeautifulSoup(main_page.content, "html.parser")

# find the links for each sub-category
categories = soup.find("li", class_="selected").find_all("li")
categories_urls = [category.find("a").get("href") for category in categories]

if continue_extract:
	extracted_category_url, extracted_pages_url = read_csv()
	image_captions = json.load(open("./peir_gross/peir_gross_captions.json"))
	image_tags = json.load(open("./peir_gross/peir_gross_tags.json"))
else:
	create_csv()
	image_captions = {}
	image_tags = {}

# go to each sub-category and extract images from the Gross sub-collection
for url in categories_urls:
	if continue_extract:
		if url in extracted_category_url:
			print('category:{} already extracted'.format(url))
			continue
	print('start to extracted {}'.format(url))
	i = 1
	image_sum = 0

	category_url = base_url + "/" + url
	category_page = s.get(category_url)
	category_soup = BeautifulSoup(category_page.content, "html.parser")

	# find the Gross sub-collection, if it exists
	collections_urls = {}
	collections = category_soup.find("li", class_="selected").find_all("li")
	for collection in collections:
		name = collection.find("a").get_text()
		collection_url = collection.find("a").get("href")
		collections_urls[name] = collection_url

	if "Gross" in list(collections_urls.keys()):
		# the page of Gross sub-collection to start extracting images from
		page_url = base_url + "/" + collections_urls["Gross"]
		page = s.get(page_url)
		page_soup = BeautifulSoup(page.content, "html.parser")
		if continue_extract:
			while True:
				if page_url in extracted_pages_url:
					print('page {} already extracted'.format(page_url))
					page_url = base_url + "/" + page_soup.find("a", rel="next").get("href")
					page = s.get(page_url, stream=True)
					page_soup = BeautifulSoup(page.content, "html.parser")
				else:
					break

		# the url of the last page or empty if there is only one page
		last_page = page_soup.find("a", rel="last")
		if last_page is None:
			last_page_url = ""
		else:
			last_page_url = base_url + "/" + last_page.get("href")

		# get the images from all the pages
		while True:

			# find the links to the images of the current page
			thumbnails = page_soup.find("ul", class_="thumbnails").find_all("a")

			for thumbnail in thumbnails:
				# get the image url
				image_url = base_url + "/" + thumbnail.get("href")
				# go to the image page and extract the data
				image_page = s.get(image_url)
				image_soup = BeautifulSoup(image_page.content, "html.parser")

				image = image_soup.find("img", id="theMainImage")
				filename = image.get("alt")
				image_src = image.get("src")
				if image_src.endswith("gif"):
					image_src = image.get("data-src")
					print(image_src)
				description = image.get("title").replace("\r\n", " ")

				tags_container = image_soup.find("div", {"id":"Tags"})
				tags = [tag.string for tag in tags_container.findChildren("a")]
				if filename in image_existed:
					image_captions[filename] = description
					image_tags[filename] = tags
					print("{} already exist".format(filename))
					continue
				# save the image to images folder
				with open( "peir_gross/peir_gross_images/" + filename, "wb") as f:
					try:
						image_file = s.get(base_url + "/" + image_src)
						f.write(image_file.content)
						# img = Image.open(f.name)
						# if img.size[0] < 300:
						# 	print("{} is invaild".format(filename))
						# 	continue
						image_captions[filename] = description
						image_tags[filename] = tags
						print(filename)
					except requests.exceptions.ConnectionError:
						print("Connection refused:{}".format(filename))

			print("Extracted", len(thumbnails), "image-caption pairs from page", i)
			write_csv(['', page_url])
			print('Finished {}'.format(page_url))
			# save captions and tags into json files after downloading one page
			save_captions(image_captions, image_tags)
			image_sum = image_sum + len(thumbnails)
			i += 1

			# if the current page is the last page stop
			if page_url == last_page_url or last_page_url == "":
				print("This was the last page")
				break

			# go to the next page
			page_url = base_url + "/" + page_soup.find("a", rel="next").get("href")
			page = s.get(page_url)
			page_soup = BeautifulSoup(page.content, "html.parser")

		write_csv([url, ''])
		print("Visited", i-1, "pages of Gross sub-collection")
		print("Extracted", image_sum, "image-caption pairs from the", category_soup.find("li", class_="selected").find("a").get_text(), "category")
	print('Finished {}'.format(url))

# with open("peir_gross/peir_gross.tsv", "w") as output_file:
# 	for image in image_captions:
# 		output_file.write(image + "\t" + image_captions[image])
# 		output_file.write("\n")
#
# print("Wrote all", len(image_captions), "image-caption pairs to tsv.")
#
# # split to train and test
# random.seed(42)
# keys = list(image_captions.keys())
# random.shuffle(keys)
#
# train_split = int(numpy.floor(len(image_captions) * 0.9))
#
# train_keys = keys[:train_split]
# test_keys = keys[train_split:]
#
# split_images(image_captions, train_keys, "peir_gross/train_images.tsv")
# split_images(image_captions, test_keys, "peir_gross/test_images.tsv")