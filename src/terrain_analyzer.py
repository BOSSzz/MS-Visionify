import math, pickle, os


class PathAnalyzer:
    """Class to process map terrain and parse information from coordinates
    Commonly used terms:
    Instance platform: member of list self.platforms format: [(x1, y1), (x2,y2)] of a platform. Used as key
        to identify indivual platforms."""
    def __init__(self):
        """Difference between platforms and oneway_platforms
        platforms can be navigation mapped to other platforms, but to to oneway_platforms
        oneway_platforms can be navigation mapped only to platforms, and not to other oneway_platforms"""
        self.platforms = [] # Format: [(x1, y1), (x2, y2)] (x1<x2)
        self.oneway_platforms = []
        self.ladders = []
        self.visited_coordinates = []
        self.current_platform_coords = []
        self.current_oneway_coords = []
        self.current_ladder_coords = []
        self.navigation_map = {}  # {((10,20),(15,20)):{[(((18,18),(25,18)),(15,20), (15,20), "jumpr"),0]}}
        self.last_x = None
        self.last_y = None
        self.movement = None

        self.determination_accuracy = 0  # Offset to determine y coord accuracy NOT USED
        self.platform_variance = 3
        self.ladder_variance = 2
        self.minimum_platform_length = 10  # Minimum x length of coordinates to be logged as a platform by input()
        self.minimum_ladder_length = 5  # Minimum y length of coordinated to be logged as a ladder by input()

        self.doublejump_max_height = 31  # total absolute jump height is about 31, but take account platform size
        self.jump_range = 16  # horizontal jump distance is about 9~10 EDIT:now using glide jump which has more range
        self.dbljump_half_height = 20  # absolute jump height of a half jump. Used for generating navigation map

    def save(self, filename="mapdata.platform", minimap_roi = None):
        """Save platforms, oneway_platforms, ladders, minimap_roi to a file
        :param filename: path to save file
        :param minimap_roi: tuple or list of onscreen minimap bounding box coordinates which will be saved"""
        with open(filename, "wb") as f:
            pickle.dump({"platforms" : self.platforms, "oneway": self.oneway_platforms, "minimap" : minimap_roi}, f)

    def load(self, filename="mapdata.platform"):
        """Open a map data file and load data from file
        :param filename: Plath to map data file
        :return boundingRect tuple of minimap as stored on file"""
        if os.path.exists(filename):
            with open(filename, "rb") as f:
                data = pickle.load(f)
                self.platforms = data["platforms"]
                self.oneway_platforms = data["oneway"]
                minimap_coords = data["minimap"]
            return minimap_coords 

    def calculate_navigation_map(self):
        """Generates a navigation map, which is a dictionary with platform as keys and a dictionary of a list[strategy, 0]"""
        for platform in self.platforms+self.oneway_platforms:
            croutes = []
            available_routes = self.find_available_moves(platform)
            for route in available_routes:
                croutes.append([route, 0])
            self.navigation_map[platform] = croutes

    def move_platform(self, from_platform, to_platform):
        """Update navigation map visit counter to keep track of visited platforms when moded
        :param from_platform: departing platform instance
        :param to_platform: destination platform instance"""
        for key in self.navigation_map.keys():
            need_reset = True
            for route in self.navigation_map[key]:
                if route[0] == to_platform:
                    route[2] = 1
                if route[2] == 0:
                    need_reset = False
            if need_reset:
                for route in self.navigation_map[key]:
                    route[2] = 0

    def input_oneway_platform(self, inp_x, inp_y):
        """input values to use in finding one way(platforms which can't be a destination platform)
        Refer to input() to see how it works
        :param inp_x: x coordinate to log
        :param inp_y: y coordinate to log"""
        converted_tuple = (inp_x, inp_y)
        if converted_tuple not in self.visited_coordinates:
            self.visited_coordinates.append(converted_tuple)

        # check if in continous platform
        if inp_y == self.last_y and self.last_x >= self.last_x - self.platform_variance and self.last_x <= self.last_x + self.platform_variance:
            # check if current coordinate is within platform being tracked
            if converted_tuple not in self.current_oneway_coords:
                self.current_oneway_coords.append(converted_tuple)
        else:
            # current coordinates do not belong in any platforms
            # terminate pending platform, if exists and create new pending platform
            if len(self.current_oneway_coords) >= self.minimum_platform_length:
                platform_start = min(self.current_oneway_coords, key=lambda x: x[0])
                platform_end = max(self.current_oneway_coords, key=lambda x: x[0])

                self.oneway_platforms.append((platform_start, platform_end))
            self.current_oneway_coords = []
            if converted_tuple not in self.visited_coordinates:
                self.current_oneway_coords.append(converted_tuple)

    def input(self, inp_x, inp_y):
        """Use player minimap coordinates to determine start and end of platforms
        This function logs player minimap marker coordinates in an attempt to identify platform coordinates from them.
        Player coordinates are temoporarily logged to self.current_platform_coords until a platform is determined for
        the given set of coordinates.
        Given that all platforms are parallel to the ground, meaning all coordinates of the platform are on the same
        elevation, a collection of input player coordinates are deemed to be on a same platform until a change in y
        coordinates is detected.
        :param inp_x: x player minimap coordinate to log
        :param inp_y: y player minimap coordinate to log"""
        converted_tuple = (inp_x, inp_y)
        if converted_tuple not in self.visited_coordinates:
            self.visited_coordinates.append(converted_tuple)

        # check if in continous platform
        if inp_y == self.last_y and self.last_x >= self.last_x - self.platform_variance and self.last_x <= self.last_x + self.platform_variance:
            # check if current coordinate is within platform being tracked
            if converted_tuple not in self.current_platform_coords:
                self.current_platform_coords.append(converted_tuple)
        else:
            # current coordinates do not belong in any platforms
            # terminate pending platform, if exists and create new pending platform
            if len(self.current_platform_coords) >= self.minimum_platform_length:
                platform_start = min(self.current_platform_coords, key=lambda x: x[0])
                platform_end = max(self.current_platform_coords, key=lambda x: x[0])

                self.platforms.append((platform_start, platform_end))
            self.current_platform_coords = []
            if converted_tuple not in self.visited_coordinates:
                self.current_platform_coords.append(converted_tuple)

        # check if in continous ladder
        if inp_x == self.last_x and inp_y >= self.last_y - self.ladder_variance and inp_y <= self.last_y + self.ladder_variance:
            # current coordinate is within pending group of coordinates for a ladder or a rope or whatever
            if converted_tuple not in self.current_ladder_coords:
                self.current_ladder_coords.append(converted_tuple)
        else:
            # current coordinates do not belong in any ladders or ropes
            # terminate ladder or ropes
            if len(self.current_ladder_coords) >= self.minimum_ladder_length:
                ladder_start = min(self.current_ladder_coords, key=lambda x: x[1])
                ladder_end = max(self.current_ladder_coords, key=lambda x: x[1])
                self.ladders.append((ladder_start, ladder_end))
            self.current_ladder_coords = []
            if converted_tuple not in self.visited_coordinates:
                self.current_ladder_coords.append(converted_tuple)
        self.last_x = inp_x
        self.last_y = inp_y

    def find_available_moves(self, platform):
        """Find relationships between platform, like how one platform links to another using movement.
        : param platform : platform item in self.platforms (tuple of 2 coordinate tuples)
        : return : list [destination_platform, (x1, y1), (x2, y2), method] where
        destination_platform : platform object in self.platforms which is the destination
        x, y : coordinate area where the method can be used (x1<=coord_x<=x2, y1<=coord_y<=y2)
        method : movement method string
            drop : drop down directly
            jmpr : right jump
            jmpl : left jump
            dbljmp_max : double jump up fully
            dbljmp_half : double jump a bit less
        """

        return_map_dict = []

        for other_platform in self.platforms:
            if platform != other_platform:
                # 1. Detect vertical overlaps
                if platform[0][0] < other_platform[1][0] and platform[1][0] > other_platform[0][0] or \
                        platform[0][0] > other_platform[0][0] and platform[0][0] < other_platform[1][0]:
                    lower_bound_x = max(platform[0][0], other_platform[0][0])
                    upper_bound_x = min(platform[1][0], other_platform[1][0])
                    if platform[0][1] < other_platform[1][1]:
                        # Platform is higher than current_platform. Thus we can just drop
                        solution = [other_platform, (lower_bound_x, platform[0][1]), (upper_bound_x, platform[0][1]), "drop"]
                        return_map_dict.append(solution)
                    else:
                        # We need to use double jump to get there, but first check if within jump height
                        if abs(platform[0][1] - other_platform[0][1]) <= self.dbljump_half_height:
                            solution = [other_platform, (lower_bound_x, platform[0][1]), (upper_bound_x, platform[0][1]), "dbljmp_half"]
                            return_map_dict.append(solution)
                        elif abs(platform[0][1] - other_platform[0][1]) <= self.dbljump_half_height:
                            solution = [other_platform, (lower_bound_x, platform[0][1]), (upper_bound_x, platform[0][1]), "dbljmp_max"]
                            return_map_dict.append(solution)
                else:
                    # 2. No vertical overlaps. Calculate euclidean distance between each platform endpoints
                    front_point_distance = math.sqrt((platform[0][0]-other_platform[1][0])**2 + (platform[0][1]-other_platform[1][1])**2)
                    if front_point_distance <= self.jump_range:
                        # We can jump from the left end of the platform to goal
                        solution = [other_platform, (platform[0][0], platform[0][1]), (platform[0][0], platform[0][1]), "jmpl"]
                        return_map_dict.append(solution)
                    back_point_distance = math.sqrt((platform[1][0]-other_platform[0][0])**2 + (platform[1][1]-other_platform[0][1])**2)
                    if back_point_distance <= self.jump_range:
                        # We can jump fomr the right end of the platform to goal platform
                        solution = [other_platform, (platform[1][0], platform[1][1]), (platform[1][0], platform[1][1]), "jmpr"]
                        return_map_dict.append(solution)

        return return_map_dict

    def reset(self):
        self.platforms = []
        self.visited_coordinates = []
        self.current_platform_coords = []
        self.current_ladder_coords = []
        self.ladders = []

