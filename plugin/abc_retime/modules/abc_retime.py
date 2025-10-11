# built in imports
import c4d, json
from math import floor

# tag/object ids
mograph_cache_tag = 1019337
point_cache_tag = 1021302
alembic_obj = c4d.Oalembicgenerator
alembic_tag = 1037184
xp_cache = 1028775

class abc_retime(c4d.plugins.TagData):
    
    #self.SetOptimizeCache(False)

    # built in functions
    def __init__(self):
        pass

    def Init(self, op):
        self.InitAttr(op, int, c4d.ABC_START_FRAME)
        self.InitAttr(op, int, c4d.ABC_OFFSET)
        self.InitAttr(op, float, c4d.ABC_SPEED)
        self.InitAttr(op, bool, c4d.ABC_APPLY_CHILDREN)
        self.InitAttr(op, int, c4d.ABC_RESET_CHILDREN)
        self.InitAttr(op, bool, c4d.ABC_RETIME_TYPE)
        self.InitAttr(op, float, c4d.ABC_FRAME)

        # defaults
        op[c4d.ABC_SPEED] = 1.0

        op[c4d.ABC_RETIME_TYPE] = 1

        bc = c4d.BaseContainer()

        return True

    # show/hide speed/frame parameter
    def GetDDescription(self, node, description, flags):
        if not description.LoadDescription(node.GetType()):
            return False  

        singleID = description.GetSingleDescID()  

        for idx, i in enumerate([c4d.ABC_FRAME, c4d.ABC_SPEED]):
            paramID = c4d.DescID(c4d.DescLevel(i))

            if singleID is None or paramID.IsPartOf(singleID)[0]:  
                bc = description.GetParameterI(paramID, None)   
                if node[c4d.ABC_RETIME_TYPE]:
                    bc[c4d.DESC_HIDE] = idx!=0
                else:
                    bc[c4d.DESC_HIDE] = idx==0

        return (True, flags | c4d.DESCFLAGS_DESC_LOADED)

    # enable/disable start frame
    def GetDEnabling(self, node, id, t_data, flags, itemdesc):
        data = node.GetDataInstance()
        if data is None:
            return

        ID = id[0].id

        retime_type = node[c4d.ABC_RETIME_TYPE]

        if ID in [c4d.ABC_START_FRAME, c4d.ABC_OFFSET]:
            return not retime_type

        # elif ID == c4d.ABC_START_FRAME:
        #     return retime_type

        return True

    def Execute(self, op, doc, obj, bt, priority, flags):
        if op is None:
            return c4d.EXECUTIONRESULT_OK

        # set G variables
        self.op = op
        self.obj = obj

        self.doc = doc
        self.fps = doc.GetFps()
        self.doc_time = doc.GetTime()
        self.doc_frame = self.doc_time.GetFrame(self.fps)
        self.start_frame = op[c4d.ABC_START_FRAME]
        
        # get basetime from frame parm
        if op[c4d.ABC_RETIME_TYPE]:
            _output = self.baseTime(op[c4d.ABC_FRAME])

            # _output += c4d.BaseTime(
            #     op[c4d.ABC_OFFSET], self.fps
            # )


        # calculate frame from speed
        else:
            _output, _mix = self.calcFrame()
        
        # apply to objects
        if op[c4d.ABC_APPLY_CHILDREN]:
            for child in IterateHierarchy(obj):
                self.setTimeValue(child, _output)

        else:
            self.setTimeValue(obj, _output)

        return c4d.EXECUTIONRESULT_OK

    def Message(self, op, type, data):
        if type == c4d.MSG_DESCRIPTION_COMMAND:
            id = data.get('id')
            if id:
                id = id[0].id

                obj = op.GetObject()

                if id == c4d.ABC_START_FROM_DOC:
                    op[c4d.ABC_START_FRAME] = \
                        self.doc.GetLoopMinTime().GetFrame(self.fps)

                elif id == c4d.ABC_RESET_CHILDREN:
                    resetABC(obj)

                elif id == c4d.ABC_IMPORT_RETIME_CLIPBOARD:
                    import_retime(op, self.doc, True)

                elif id == c4d.ABC_IMPORT_RETIME_FILE:
                    import_retime(op, self.doc)

        return True
    
    def baseTime(self, frame):
        '''
        return unquantized basetime
        '''
        value = c4d.BaseTime(frame)
        value /= self.fps
        return value

    def calcFrame(self):
        '''
        calculate and return c4d.BaseTime when speed mode is enabled
        '''
        # self.op variables
        start_frame = self.start_frame
        offset = self.baseTime(self.op[c4d.ABC_OFFSET])
        speed = self.op[c4d.ABC_SPEED]
        doc_frame = self.doc_frame
        single_frame = c4d.BaseTime(1, self.fps)

        start_time = self.baseTime(start_frame)
        doc_time = self.doc.GetTime()
        
        # return if playhead before start frame
        if doc_frame < start_frame:
            start_time += offset
            return start_time, 0.0
        
        _output = start_time

        ## read anim track and calculate frame offset (_output)

        # find speeds anim track
        speed_id = c4d.DescID(c4d.DescLevel(c4d.ABC_SPEED))
        speed_track = self.op.FindCTrack(speed_id)

        # existing anim track - read keyframes
        if speed_track:

            # check playhead is within the frame range
            if doc_frame > start_frame:
                keys = []

                breakout = False

                speed_curve = speed_track.GetCurve()

                cur_value = start_time

                # check value at start frame
                keys.append([
                    c4d.BaseTime(start_frame, self.fps),
                    speed_curve.GetValue(start_time)
                ])

                for k in range(speed_curve.GetKeyCount()):
                    # break when doc_frame has been found in prior loop
                    if breakout:
                        break

                    # get current keyframe values
                    key = speed_curve.GetKey(k)
                    time = key.GetTime()

                    # skip frames that exist before start frame
                    if time.GetFrame(self.fps) < start_frame:
                        continue

                    # skip frames that exist on the start frame
                    # we set this value before the loop
                    elif time.GetFrame(self.fps) == start_frame:
                        continue

                    # calculate inbetween frames
                    last_frame = keys[-1][0].GetFrame(self.fps) + 1
                    cur_frame = key.GetTime().GetFrame(self.fps)
                    t = []

                    for f in range(last_frame, (cur_frame + 1)):
                        t.append(f)
                        if f != start_frame:
                            cur_value += single_frame * c4d.BaseTime(speed_curve.GetValue(c4d.BaseTime(f, self.fps)))
                            keys.append([
                                c4d.BaseTime(f, self.fps),
                                cur_value
                            ])

                        if f == doc_frame:
                            _output = cur_value
                            breakout = True
                            break

                # add final sustain frame
                if not breakout:
                    s = keys[-1][0]
                    diff = doc_time - s
                    diff *= c4d.BaseTime(speed_curve.GetValue(s))

                    _output = cur_value + diff

        # no anim track - constant speed
        else:
            # check playhead is within the frame range
            if doc_frame > start_frame:
                diff = doc_time - start_time
                diff *= c4d.BaseTime(speed)

                _output = start_time + diff

        # apply post offset to _output
        _output += offset

        ## get mix values
        Min = floor(_output.GetFrame(self.fps))

        _mix = abs(_output.GetFrame(self.fps) - Min)
        # return (Min - start_frame), _mix
        return _output, _mix

    def setTimeValue(self, obj, _output):

        # no object
        if obj == None:
            return

        # mograph cache tag
        elif obj.GetTag(mograph_cache_tag):
            _output -= self.doc_time

            tag = obj.GetTag(mograph_cache_tag)
            cleanTrack(tag, c4d.MGCACHETAG_OFFSET)
            tag[c4d.MGCACHETAG_OFFSET] = _output

        # point cache tag
        elif obj.GetTag(point_cache_tag):
            _output -= self.doc_time

            tag = obj.GetTag(point_cache_tag)
            cleanTrack(tag, c4d.ID_CA_GEOMCACHE_TAG_CACHE_OFFSET)
            tag[c4d.ID_CA_GEOMCACHE_TAG_CACHE_OFFSET] = _output

        # alembic
        elif obj.GetType() == alembic_obj:
            cleanTrack(obj, c4d.ALEMBIC_USE_ANIMATION)
            cleanTrack(obj, c4d.ALEMBIC_INTERPOLATION)
            cleanTrack(obj, c4d.ALEMBIC_ANIMATION_FRAME)
            obj[c4d.ALEMBIC_USE_ANIMATION] = False
            obj[c4d.ALEMBIC_INTERPOLATION] = True
            obj[c4d.ALEMBIC_ANIMATION_FRAME] = _output

        # alembic tag
        elif obj.GetTag(alembic_tag):
            tag = obj.GetTag(alembic_tag)
            cleanTrack(obj, c4d.ALEMBIC_MT_USE_ANIMATION)
            cleanTrack(obj, c4d.ALEMBIC_MT_INTERPOLATION)
            cleanTrack(obj, c4d.ALEMBIC_MT_ANIMATION_FRAME)
            tag[c4d.ALEMBIC_MT_USE_ANIMATION] = False
            tag[c4d.ALEMBIC_MT_INTERPOLATION] = True
            tag[c4d.ALEMBIC_MT_ANIMATION_FRAME] = _output
            

        # xp cache
        elif obj.GetType() == xp_cache:
            cleanTrack(obj, c4d.XOCA_CACHE_RETIMING)
            cleanTrack(obj, c4d.XOCA_CACHE_TIME)
            obj[c4d.XOCA_CACHE_RETIMING] = 2
            obj[c4d.XOCA_CACHE_TIME] = _output.Get()

def import_retime(op, doc, clipboard=False):
    '''
    import data from another application
    https://github.com/axisfx2/cross-platform-retime
    '''
    if clipboard:
        data = c4d.GetStringFromClipboard()

    else:# file
        file = get_file()

        if not file:
            return

        try:
            with open(file, 'r') as f:
                data = f.read()
        except:
            popup('ERROR: failed to read file')
            return
    
    # verify if data is valid
    msg = 'ERROR: invalid retime data'

    try:
        data = json.loads(data)
    except:
        popup(msg)
        return

    if not isinstance(data, list):
        popup(msg)
        return

    # find speeds anim track
    speed_id = c4d.DescID(c4d.DescLevel(c4d.ABC_FRAME))
    speed_track = op.FindCTrack(speed_id)

    doc.StartUndo()

    # existing anim track - read keyframes
    if speed_track != None:
        speed_track.Remove()

    # add track
    speed_track = c4d.CTrack(op, speed_id)

    op.InsertTrackSorted(speed_track)

    curve = speed_track.GetCurve()

    # time variables
    fps = doc.GetFps()
    cur_time = doc.GetMinTime()
    incr = c4d.BaseTime(1, fps)

    # add keyframes from list
    for frame in data:
        time = c4d.BaseTime(float(frame / fps))

        # Creates a keyframe in the memory
        key = c4d.CKey()
        
        # Fills the key with the default data
        speed_track.FillKey(doc, op, key)
        
        # Defines the y value
        key.SetGeData(curve, time)
        
        # Defines the time value
        key.SetTime(curve, cur_time)
        
        # Adds a key on the curve for the given frame
        curve.InsertKey(key)

        # shift current time by 1 frame
        cur_time += incr

    # set retime type
    op[c4d.ABC_RETIME_TYPE] = 1

    doc.EndUndo()

def popup(msg):
    c4d.gui.MessageDialog(msg)

def get_file():
    file = c4d.storage.LoadDialog(
        type=c4d.FILESELECTTYPE_ANYTHING,
        title='Retime file'
    )

    return file

def resetABC(op):
    children = IterateHierarchy(op)

    for obj in children:
        if obj != op:
            # alembic
            if obj.GetType() == alembic_obj:
                c4d.CallButton(obj, c4d.ALEMBIC_ANIMATION_RESET)
            
            # xp cache
            elif obj.GetType() == xp_cache:
                obj[c4d.XOCA_CACHE_TIME] = 0
 
def IterateHierarchy(op):
    '''
    hierarchy iteration
    https://developers.maxon.net/?p=596
    '''
    def GetNextObject(op):
        if op==None:
            return None
    
        if op.GetDown():
            return op.GetDown()
    
        while not op.GetNext() and op.GetUp():
            op = op.GetUp()
    
        return op.GetNext()
    
    if op is None:
        return
 
    children = []

    while op:
        children.append(op)
        op = GetNextObject(op)
 
    return children

def cleanTrack(op, id):
    '''
    delete track (all keyframes) of specified parameter
    '''
    # find speeds anim track
    speed_id = c4d.DescID(c4d.DescLevel(id))
    speed_track = op.FindCTrack(speed_id)

    # existing anim track - read keyframes
    if speed_track != None:
        speed_track.Remove()
        return True
    return False